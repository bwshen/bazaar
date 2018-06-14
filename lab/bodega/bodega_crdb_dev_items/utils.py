"""Utility functions for Bodega CockroachDB items."""
from bodega_aws.utils import search_for_ami_id_by_name


def get_ami_id_for_cockroachdb_deps_machine(aws_farm, image_version):
    if not image_version.startswith('cockroachdb'):
        image_version = 'cockroachdb_deps_' + image_version
    return search_for_ami_id_by_name(aws_farm, image_version)
