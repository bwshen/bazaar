"""Utility functions for Bodega AWS."""
import logging
from datetime import timedelta

import boto3
from bodega_core.exceptions import bodega_value_error
from bodega_core.models import Item, Network
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from memoize import memoize
from .models import AwsFarm

NUM_AWS_API_RETRY_ATTEMPTS = 15
BASE_URL = 'https://%s' % settings.ALLOWED_HOSTS[0]
log = logging.getLogger(__name__)


def _get_ec2_client_for_farm(farm):
    session = boto3.session.Session(
        region_name=farm.region_name,
        aws_access_key_id=farm.aws_access_key_id,
        aws_secret_access_key=farm.aws_secret_access_key)
    config = Config(retries={'max_attempts': NUM_AWS_API_RETRY_ATTEMPTS})
    return session.client('ec2', config=config)


def _get_ec2_instance_from_aws(ec2_instance):
    ec2_client = _get_ec2_client_for_farm(
        ec2_instance.farm)
    response = ec2_client.describe_instances(
        InstanceIds=[
            ec2_instance.instance_id
        ]
    )
    instance = response['Reservations'][0]['Instances'][0]
    return instance


def _get_instance_ami_image_from_aws(ec2_instance):
    ec2_client = _get_ec2_client_for_farm(
        ec2_instance.farm)
    response = ec2_client.describe_images(
        ImageIds=[
            ec2_instance.ami_id
        ]
    )
    image = response['Images'][0]
    return image


def get_or_create_aws_network(vpc_id, location):
    try:
        network = Network.objects.get(name=vpc_id, location=location)
        return network
    except ObjectDoesNotExist:
        log.debug('Network with name of %s and location %s does not exist '
                  'so creating it now.' % (vpc_id, location.name))
        network = Network.objects.create(name=vpc_id, location=location)
        return network


def get_aws_farm(location):
    if location.name.lower().startswith('aws-'):
        # Strip off the 'aws-' prefix to get the aws region name
        region_name = location.name.lower()[4:]
        return AwsFarm.objects.get(region_name=region_name)
    bodega_value_error(log, 'Unexpected location value of %s.' % location.name)


def get_ec2_instance_type_for_model(model):
    """Get the instance type for CdmNodes in AWS."""
    if 'm4.large' in model:
        return 'm4.large'
    elif 'm4.xlarge' in model:
        return 'm4.xlarge'
    elif 'm4.2xlarge' in model:
        return 'm4.2xlarge'
    elif 't2.large' in model:
        return 't2.large'
    else:
        raise bodega_value_error(
            log,
            '%s is not a supported model type for AWS' % model)


@memoize(timeout=timedelta(minutes=15).total_seconds())
def get_ec2_instance_private_ip(ec2_instance):
    aws_ec2_instance = _get_ec2_instance_from_aws(ec2_instance)
    return aws_ec2_instance['PrivateIpAddress']


def delete_ec2_instance(ec2_instance):
    ec2_client = _get_ec2_client_for_farm(ec2_instance.farm)

    if not ec2_instance.instance_id:
        log.warning('%s did not have an associated instance_id. We may be '
                    'leaking Ec2Instances on AWS.' % ec2_instance)
        # Cannot retroactively assign this Ec2Instance to the correct
        # instance it represents in AWS so just mark it as DESTROYED
        ec2_instance.state = Item.STATE_DESTROYED
        ec2_instance.save()
        return

    ec2_client.terminate_instances(
        InstanceIds=[
            ec2_instance.instance_id
        ]
    )
    log.info('Waiting for ec2 instance with id of %s to terminate.'
             % ec2_instance.instance_id)
    waiter = ec2_client.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=[ec2_instance.instance_id])
    log.info('ec2 instance %s successfully terminated.'
             % ec2_instance.instance_id)
    ec2_instance.state = Item.STATE_DESTROYED
    ec2_instance.save()


def create_ec2_instance_on_aws(ec2_instance,
                               additional_disk_size=0,
                               sda1_volume_size=None,
                               instance_block_device_mappings=None,
                               ebs_optimized=False):
    if instance_block_device_mappings is None:
        instance_block_device_mappings = []

    ec2_client = _get_ec2_client_for_farm(ec2_instance.farm)

    image = _get_instance_ami_image_from_aws(ec2_instance)
    tags = [
        {
            'Key': 'Name',
            'Value': ec2_instance._name
        },
        {
            'Key': 'Purpose',
            'Value': 'Created by Bodega'
        },
        {
            'Key': 'Bodega Instance',
            'Value': BASE_URL
        }
    ]

    if 'Tags' in image:
        tags = tags + image['Tags']
    tag_specifications = [
        {
            'ResourceType': 'instance',
            'Tags': tags,
        }
    ]

    run_instance_args = {
        'ImageId': ec2_instance.ami_id,
        'InstanceType': ec2_instance.instance_type,
        'TagSpecifications': tag_specifications,
        'MinCount': 1,
        'MaxCount': 1,
        'BlockDeviceMappings': instance_block_device_mappings,
        'SubnetId': ec2_instance.farm.subnet_id,
        'SecurityGroupIds': [ec2_instance.farm.security_group_id]
    }
    log.debug('Run instance args: %s' % run_instance_args)

    if additional_disk_size:
        block_device_mappings = run_instance_args.get(
            'BlockDeviceMappings', [])

        # If there are volumes in the AMI, we can't assume attaching
        # /dev/sdb will succeed, since AMI can already have a volume
        # mapped to this device. For this reason, use assert below.
        if block_device_mappings:
            bodega_value_error(
                log,
                'Block device mapping is not empty: %s'
                % block_device_mappings)

        block_device_mappings.append({
            'DeviceName': '/dev/sdb',
            'Ebs': {
                'VolumeSize': additional_disk_size,
                'VolumeType': 'gp2',
                'DeleteOnTermination': True
            }
        })
        run_instance_args['BlockDeviceMappings'] = block_device_mappings

    if sda1_volume_size is not None:
        block_device_mappings = run_instance_args.get(
            'BlockDeviceMappings', [])
        block_device_mappings.append({
            'DeviceName': '/dev/sda1',
            'Ebs': {
                'VolumeSize': sda1_volume_size
            }
        })
        run_instance_args['BlockDeviceMappings'] = block_device_mappings

    if ebs_optimized:
        run_instance_args['EbsOptimized'] = True

    try:
        response = ec2_client.run_instances(**run_instance_args)
        instance = response['Instances'][0]
        instance_id = instance['InstanceId']

        ec2_instance.instance_id = instance_id
        ec2_instance.save()

        log.info('ec2 instance created with id of %s. Waiting for Status OK'
                 % instance_id)
        waiter = ec2_client.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[instance_id])
        log.debug('ec2 instance %s has status OK.' % instance_id)
        return instance
    except:
        log.error('Caught error while trying to create Ec2Instance with '
                  'image: %s, instance_type: %s, name: %s, instance_id: %s. '
                  'Deleting it if it exists.'
                  % (ec2_instance.ami_id, ec2_instance.instance_type,
                     ec2_instance.name, ec2_instance.instance_id),
                  exc_info=True)
        delete_ec2_instance(ec2_instance)
        raise


def tag_ec2_instance(ec2_instance, key, value):
    ec2_client = _get_ec2_client_for_farm(ec2_instance.farm)
    tags = [{'Key': key, 'Value': value}]

    log.debug('Tagging %s with %s' % (ec2_instance, tags))
    ec2_client.create_tags(
        Resources=[ec2_instance.instance_id],
        Tags=tags
    )


@memoize(timeout=timedelta(minutes=15).total_seconds())
def get_ec2_instance_tags(ec2_instance):
    aws_ec2_instance = _get_ec2_instance_from_aws(ec2_instance)
    return aws_ec2_instance['Tags']


def get_ec2_instance_tag_value(ec2_instance, key):
    tags = get_ec2_instance_tags(ec2_instance)
    for tag in tags:
        if tag['Key'] == key:
            return tag['Value']
    bodega_value_error(log,
                       'Did not find key %s in tags for %s'
                       % (key, ec2_instance))


def search_for_ami_id_by_name(farm, ami_name):
    log.debug('Searching for AMI with name of %s' % ami_name)
    ec2 = _get_ec2_client_for_farm(farm)
    describe_image_response = ec2.describe_images(
        Filters=[{'Name': 'name', 'Values': [ami_name]}])
    image_search_results = describe_image_response['Images']
    if len(image_search_results) == 0:
        error_message = 'Could not find %s ami in AwsFarm %s' % \
            (ami_name, farm.region_name)
        bodega_value_error(log, error_message)
    if len(image_search_results) > 1:
        error_message = 'Found more than one %s in AwsFarm %s' % \
            (ami_name, farm.region_name)
        bodega_value_error(log, error_message)
    return image_search_results[0]['ImageId']
