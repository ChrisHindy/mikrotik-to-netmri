#!/usr/bin/env python3
"""Get config from a Mikrotik over SSH and put it into NetMRI."""

# Author: Chris Hindy (chindy@empowerednetworks.com)
# Copyright (c) 2018, Empowered Networks Inc. We provide this AS-IS with NO WARRANTY.

import argparse
import select
import sys
import configparser
import paramiko
from paramiko import SSHClient
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

def get_args(args=None):
    """Deal with command line arguments."""
    parser = argparse.ArgumentParser(
        description='Get config from a device over SSH and put it into NetMRI.'
        )
    parser.add_argument('-I', '--ipaddress',
                        help='IP Address of the target device.',
                        required='True')

    results = parser.parse_args(args)
    return {'ipaddress':results.ipaddress}

def get_config():
    """Read our config file for local settings."""
    config = configparser.SafeConfigParser()
    config.read("mikrotik-to-netmri.conf")
    return config

def netmri_api_get(config, uri, payload):
    """Make a GET request to NetMRI, return the results."""
    url_path = config.get("netmri", "host") + uri
    if config.get("netmri", "use-ssl") == "yes":
        protocol = "https://"
    else:
        protocol = "http://"
    url = protocol + url_path
    # the "verify" stanza is just ignored when using http; it's consulted only for https.
    try:
        response = requests.get(url,
                                auth=requests.auth.HTTPBasicAuth(
                                    config.get("netmri", "user"),
                                    config.get("netmri", "password")),
                                params=payload,
                                verify=config.get("netmri", "ca-file")
                                )
    except requests.exceptions.SSLError:
        # Self-signed cert.  Try again with no verification.
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        response = requests.get(url,
                                auth=requests.auth.HTTPBasicAuth(
                                    config.get("netmri", "user"),
                                    config.get("netmri", "password")),
                                params=payload,
                                verify=False)
    except OSError as thiserror:
        # Specified path to CA certs is no good.
        print("Error: %s" %(thiserror))
        sys.exit(1)
    return response

def put_config_to_netmri(config, deviceid, running, saved):
    """Send in the configs to NetMRI."""
    payload = {
        'DeviceID' : deviceid,
        'RunningConfig' : running,
        'SavedConfig' : saved
        }
    uri = "/api/3.3/config_revisions/import_custom_config"
    url_path = config.get("netmri", "host") + uri
    if config.get("netmri", "use-ssl") == "yes":
        protocol = "https://"
    else:
        protocol = "http://"
    url = protocol + url_path
    try:
        response = requests.post(url,
                                 auth=requests.auth.HTTPBasicAuth(
                                     config.get("netmri", "user"),
                                     config.get("netmri", "password")),
                                 data=payload,
                                 verify=config.get("netmri", "ca-file"))
    except requests.exceptions.SSLError:
        # Self-signed cert.  Try again with no verification.
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        response = requests.post(url,
                                 auth=requests.auth.HTTPBasicAuth(
                                     config.get("netmri", "user"),
                                     config.get("netmri", "password")),
                                 data=payload,
                                 verify=False)
    except OSError as thiserror:
        # Specified path to CA certs is no good.
        print("Error: %s" %(thiserror))
        sys.exit(1)
    return response.status_code

def get_device_id(config, deviceip):
    """Given the device's IP address in dotted form, go ask NetMRI for the DeviceID."""
    querystring = {"op_DeviceIPDotted":"=",
                   "val_c_DeviceIPDotted":deviceip,
                   "select":"DeviceID"}
    uri = "/api/3.3/devices/find"
    response = netmri_api_get(config, uri, querystring)
    try:
        deviceid = response.json()["devices"][0]["DeviceID"]
    except IndexError:
        print("Error: NetMRI doens't know about a device with address %s" %(deviceip))
        sys.exit(1)
    return deviceid

def get_device_config(config, deviceip):
    """Connect to the device via ssh and pull its config in."""
    #
    # This is the function you'd want to replace with something
    # relevant to your particular device type/vendor.  So, if you
    # were dealing with Meraki, for example, you'd use a similar GET
    # pattern as in get_device_id below, substituting the correct
    # URL and API endpoint as appropriate.
    #
    try:
        sshconn = SSHClient()
        sshconn.load_system_host_keys()
        sshconn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sshconn.connect(deviceip, '22', config.get("mikrotik", "user"))
    except paramiko.ssh_exception as thiserror:
        print("Connection to %s failed. Exception was: %s" %(deviceip, thiserror))
        sys.exit(1)
    _, ssh_stdout, _ = sshconn.exec_command('/export')
    device_config = ""
    while not ssh_stdout.channel.exit_status_ready():
    # Only print data if there is data to read in the channel
        if ssh_stdout.channel.recv_ready():
            rlist, _, _ = select.select([ssh_stdout.channel], [], [], 0.0)
            if rlist:
                # Print data from stdout...it'll come in as bytes, so
                # decode it to UTF-8 text so it pretty-prints in NetMRI.
                device_config += ssh_stdout.channel.recv(1024).decode("utf-8")
    # TODO: Some exception handling is needed here for dealing with incomplete
    # returns and the like.
    sshconn.exec_command('/quit')
    sshconn.close()
    # This little bit of trickery is to deal with the wierd format we
    # get back from the MT.
    device_config.replace(r"\r\n", "\n")
    return device_config

def main():
    """Start the main loop."""
    args = get_args()
    config = get_config()
    ipaddress = args["ipaddress"]
    # Check if NetMRI knows about the target device.
    deviceid = get_device_id(config, ipaddress)
    # Get the config(s) from the device or controller.
    # The API requires both a running and saved config to be sent.
    #
    # TODO: It might be nescessary to modify get_device_config to ask for 
    #       running and saved separately (e.g. add an argument to specify which
    #       to collect from the device endpoint) or to return running and saved
    #       here seperately (e.g. return a dict a la
    #       {"running":"the_config", "saved":"the_config"})
    #
    # Mikrotik has no concept of saved config, so we just send the running config up
    # in both cases.
    device_config = get_device_config(config, ipaddress)
    device_running = device_config
    device_saved = device_config

    result = put_config_to_netmri(config, deviceid, device_running, device_saved)
    if result == 200:
        print("Uploaded config for %s to NetMRI." %(ipaddress))
    else:
        print("Error uploading config to NetMRI: %s" %(result))

if __name__ == '__main__':
    main()
