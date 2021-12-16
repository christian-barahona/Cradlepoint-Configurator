import re
from datetime import datetime, timedelta
import requests
import time
from requests.auth import HTTPDigestAuth
from subprocess import Popen, STDOUT, DEVNULL
from credentials import credentials
from os import system, name
import paramiko
import socket

ok_status = requests.codes.ok
no_content = requests.codes.no_content


class SshClient:
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password

    def command(self, command_string):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=self.host, username=self.username, password=self.password, timeout=5)
            ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command(command_string)
            ssh_stdout.channel.recv_exit_status()
            output = ssh_stdout.read()
            data = output.decode('utf-8')[1:].strip()
            client.close()
            return data
        except paramiko.ssh_exception.AuthenticationException:
            return 'SSH authentication error. Check credentials.'
        except (paramiko.SSHException, socket.error):
            return 'SSH connection error. Check connection parameters.'
        except Exception as exception:
            log_message(f"SSH session failed: {exception}")
            log_message(f"Command string used: {command_string}")
            return 'other'


def multi_print(message, file, skip_console=False):
    print(message, file=file)
    if skip_console:
        return
    print(message)


def clear_console():
    if name == 'nt':
        system('cls')
    else:
        system('clear')


def http_session(username=None, password=None, auth=None):
    session = requests.Session()
    if None not in (username, password, auth) and auth == 'digest':
        session.auth = HTTPDigestAuth(username, password)
        return session
    elif None not in (username, password, auth) and auth == 'basic':
        session.auth = (username, password)
        return session
    else:
        return session


def create_ncm_session():
    session = http_session()
    session.headers.update({
        'X-CP-API-ID': credentials.X_CP_API_ID,
        'X-CP-API-KEY': credentials.X_CP_API_KEY,
        'X-ECM-API-ID': credentials.X_ECM_API_ID,
        'X-ECM-API-KEY': credentials.X_ECM_API_KEY,
        'Content-Type': 'application/json'
    })
    return session


def delay(seconds):
    time.sleep(seconds)


def mac_address_filter(mac_address, filter_type):
    if filter_type == 'password':
        password = ''
        for character in mac_address.split("\n"):
            password = re.sub(r"[^a-zA-Z0-9]+", '', character)[-8:]
        return password

    elif filter_type == 'mac':
        mac = ''
        for character in mac_address.split("\n"):
            mac = re.sub(r"[^a-zA-Z0-9]+", '', character)
        return mac

    elif filter_type == 'validate':
        regex_type_one = r"\A[0-9A-Fa-f]{12}\Z"
        regex_type_two = r"\A([0-9A-Fa-f]{1,2}[:\- ]){5}([0-9A-Fa-f]{1,2})\Z"
        check_one = bool(re.match(regex_type_one, mac_address))
        check_two = bool(re.match(regex_type_two, mac_address))
        if check_one or check_two:
            return True
        else:
            return False


def get_time(time_type):
    if time_type == 'time':
        return datetime.now().strftime('%X')
    elif time_type == 'timestamp':
        return datetime.now()


def elapsed_time(time_start):
    time_now = datetime.now()
    time_elapsed = time_now - time_start
    return timedelta(seconds=time_elapsed.seconds)


def log_message(message, message_type=None, timestamp=None, start_time=None):
    if message_type is None:
        print(f"{get_time('time')} {message}")
    elif message_type == 'elapsed':
        print("\r" + f"{timestamp} {message}: {elapsed_time(start_time)}", end="")
    elif message_type == 'elapsed-newline':
        print("\n" + f"{timestamp} {message}: {elapsed_time(start_time)}", end="")
    elif message_type == 'newline':
        print("\n" + f"{get_time('time')} {message}")
    elif message_type == 'input':
        user_input = input(f"{get_time('time')} {message}")
        return user_input


def ping(ip_address):
    ping_response = Popen(f'ping -n 1 -w 500 {ip_address}', stdout=DEVNULL, stderr=STDOUT)
    ping_response.wait()
    response = ping_response.poll()
    return response
