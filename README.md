# mikrotik-to-netmri
Collects configuration from a [Mikrotik](https://mikrotik.com/ "Mikrotik Routers and Wireless") device and stores it in [Infoblox NetMRI](https://www.infoblox.com/products/netmri/ "Infoblox|NetMRI") (7.3.1++)

This is an example script to demonstrate the use of Infoblox's new "import_custom_config" API in NetMRI v7.3.1 and up,
It connects to a Mikrotik network device, collects the current configuration from it and publishes that 
config into NetMRI's Config Archive.

Usage:

`# mikrotik-to-netmri.py -I [ip address of Mikrotik device]`

Pre-requisites:
===============

- Python 3
- paramiko
- requests

Configuration:
==============

Edit the file mikrotik-to-netmri.conf to provide credentials for your NetMRI instance.  They need the "view_sensitive"
role for this script to work (the ChangeEngineer High, ChangeEngineer Medium, ChangeEngineer Low, ConfigAdmin, GroupManager,
Network Operator, Network Security Engineer, Policy Admin, Report Admin, Security Admin, Switch Port Administrator, SysAdmin
roles will all work)

Caveats:
========

This is an example only, and as such it doesn't do a lot of self-protection.  We provide this AS-IS with NO WARRANTY.

Contact:
========

Chris Hindy (chindy@empowerednetworks.com)

Copyright (c) 2018, Empowered Networks Inc.
