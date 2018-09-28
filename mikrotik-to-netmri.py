#!/usr/bin/env python3
"""Get config from a Mikrotik over SSH and put it into NetMRI."""

import argparse
import pprint
import select
import sys
import ConfigParser
import paramiko
from paramiko import SSHClient
import requests

def get_args(args=None):
    """Deal with command line arguments."""
    parser = argparse.ArgumentParser(description='Get config from a Mikrotik over SSH and put it into NetMRI.')
    parser.add_argument('-I', '--ipaddress',
                        help='IP Address of the Mikrotik device.',
                        required='True',
                        default='10.255.255.1')
    parser.add_argument('-N', '--netmri',
                        help='Address of the NetMRI instance.',
                        required='True',
                        default='netmri.lwpca.net')

    results = parser.parse_args(args)
    return {'ipaddress':results.ipaddress,
            'netmriaddr':results.netmri}

def get_config():
    """Read our config file for local settings."""
    config = ConfigParser.SafeConfigParser()
    config.read("mikrotik-to-netmri.conf")
    return config

def get_mikrotik_config(deviceip):
    """Connect to the Mikrotik via ssh and pull its config in."""
    # This is the function you'd want to replace with something
    # relevant to your particular device type/vendor.  So, if you
    # were dealing with Meraki, for example, you'd use a similar GET
    # pattern as in get_mt_device_id below, substituting the correct
    # URL and API endpoint as appropriate.
    # 
    # You'd obviously want to wrap this part in a try...except to
    # account for the vagaries of real life.
    sshconn = SSHClient()
    sshconn.load_system_host_keys()
    sshconn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # TODO: It'd be a good idea to externalize the username here....
    sshconn.connect(deviceip, '22', 'admin')
    ssh_stdin, ssh_stdout, ssh_stderr = sshconn.exec_command('/export')
    mt_config = ""
    while not ssh_stdout.channel.exit_status_ready():
    # Only print data if there is data to read in the channel
        if ssh_stdout.channel.recv_ready():
            rl, wl, xl = select.select([ssh_stdout.channel], [], [], 0.0)
            if rl:
                # Print data from stdout
                mt_config += ssh_stdout.channel.recv(1024).decode("utf-8")
    # TODO: Some exception handling is needed here for dealing with incomplete
    # returns and the like.
    sshconn.exec_command('/quit')
    sshconn.close()
    mt_config.replace(r"\r\n", "\n")
    return mt_config

def get_mt_device_id(netmriaddr, config, deviceip):
    """Given the device's IP address in dotted form, go ask NetMRI for the DeviceID."""
    querystring = {"op_DeviceIPDotted":"=",
                   "val_c_DeviceIPDotted":deviceip,
                   "select":"DeviceID"}
    url = "http://" + netmriaddr + "/api/3.3/devices/find"
    response = requests.get(url, auth=requests.auth.HTTPBasicAuth(
        config.get("netmri-creds", "user"),
        config.get("netmri-creds", "password")),
                            params=querystring)
    deviceid = response.json()["devices"][0]["DeviceID"]
    # TODO: Obviously you'll trap any bad responses, like if NetMRI doesn't know about the device 
    # for example before just dumbly returning.
    return deviceid

def put_config_to_netmri(netmriaddr, config, deviceid, running, saved):
    """Send in the configs to NetMRI."""
    payload = {
        'DeviceID' : deviceid,
        'RunningConfig' : running,
        'SavedConfig' : saved
        }
    url = "http://" + netmriaddr + "/api/3.3/config_revisions/import_custom_config"
    response = requests.post(url, auth=requests.auth.HTTPBasicAuth(
        config.get("netmri-creds", "user"),
        config.get("netmri-creds", "password")),
                             data=payload)
    return response.status_code

def main():
    """Start the main loop."""
    args = get_args()
    config = get_config()
    ipaddress = args["ipaddress"]
    mt_config = get_mikrotik_config(ipaddress)
    deviceid = get_mt_device_id(args["netmriaddr"], config, ipaddress)
    # You'd send running and saved here.  Mikrotik has no concept of saved config, so we
    # just send the running config up in both cases.
    result = put_config_to_netmri(args["netmriaddr"], config, deviceid, mt_config, mt_config)
    print(result)

if __name__ == '__main__':
    main()
