"""SSH utility functions for Bodega."""
import logging
from time import sleep

import paramiko

log = logging.getLogger(__name__)
USERNAME = 'ubuntu'


# Deliberately avoid using `src/py/utils/ssh_util.py in Bodega since
# a lot of its imports are fairly CDM specific. These functions
# are very similar to several functions in ssh_util.py however.
def send_remote_command(ip_address,
                        cmd,
                        username=USERNAME,
                        password=None,
                        key_filename=None,
                        port=22,
                        log_stdout=False):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log.debug('ssh connect %s username: %s port: %d, key %s' %
              (ip_address, username, port, key_filename))

    if key_filename:
        key = paramiko.RSAKey.from_private_key_file(key_filename)
        ssh.connect(ip_address,
                    username=username,
                    pkey=key,
                    port=port)
    elif password:
        ssh.connect(ip_address,
                    username=username,
                    password=password,
                    port=port)
    else:
        raise Exception('Neither key_filename or password was specified.')

    log.debug('ssh %s: %s' % (ip_address, cmd))
    (_, stdout, stderr) = ssh.exec_command(cmd)

    log.debug('Command %s successfully sent. Waiting for completion.'
              % cmd)
    channel = stdout.channel
    stdout_strs = []
    if log_stdout:
        # Log the stdout lines as they're ready. Save the standard
        # output lines since we want to return them to the caller
        while not channel.exit_status_ready():
            stdout_line = stdout.readline(1024)
            if stdout_line:
                log.debug(stdout_line)
                stdout_strs.append(stdout_line)
    status = channel.recv_exit_status()

    # Read whatever is inside the channels
    stderr_msg = stderr.read().decode('utf-8')
    stdout_lines = stdout.read().decode('utf-8')
    if log_stdout:
        log.debug(stdout_lines)
    stdout_strs.append(stdout_lines)

    if status != 0:
        raise RuntimeError('ssh %s error %d cmd %s: %s' %
                           (ip_address, status, cmd, stderr_msg))

    if len(stderr_msg) > 0:
        log.warning('Stderr: %s' % stderr_msg)

    log.debug('Ran command successfully.')
    return "".join(stdout_strs), stderr_msg


def sftp(ip_address,
         local_path,
         remote_path,
         username=USERNAME,
         password=None,
         key_filename=None,
         port=22):
    log.info('SFTP %s to %s on %s' % (local_path, remote_path, ip_address))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    log.debug('ssh connect %s username: %s port: %d' %
              (ip_address, username, port))

    if key_filename:
        key = paramiko.RSAKey.from_private_key_file(key_filename)
        ssh.connect(ip_address,
                    username=username,
                    pkey=key,
                    port=port)
    elif password:
        ssh.connect(ip_address,
                    username=username,
                    password=password,
                    port=port)
    else:
        raise Exception('Neither key_filename or password was specified.')

    sftp = ssh.open_sftp()
    sftp.put(local_path, remote_path, confirm=True)
    sftp.close()
    log.debug('Sftp to %s was successful.' % ip_address)


def check_ssh_availability(ip_address,
                           username=USERNAME,
                           password=None,
                           key_filename=None,
                           port=22,
                           retries=10,
                           interval=15):
    for iteration_count in range(retries):
        try:
            send_remote_command(ip_address,
                                'echo "hello world"',
                                username,
                                password,
                                key_filename,
                                port)
            return True
        except Exception as e:
            log.debug('Try %s of %s to check for SSH availibility on (%s) '
                      'failed with Exception %s. Sleeping for %s seconds '
                      'before trying again.'
                      % (iteration_count, retries, ip_address, e, interval),
                      exc_info=True)

            if iteration_count + 1 < retries:
                sleep(interval)
    return False
