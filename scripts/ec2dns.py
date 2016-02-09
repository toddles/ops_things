#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import boto.ec2 
import re
import update_route53


aws_region = 'us-west-2' if 'AWS_DEFAULT_REGION' not in os.environ else os.environ['AWS_DEFAULT_REGION']

try:
    ec2conn = boto.ec2.connect_to_region(aws_region)
except boto.exception.NoAuthHandlerFound:
    print("\n\n\n     AWS_SECURITY_TOKEN and AWS_ACCESS_KEY_ID are either invalid or not set.\n\n\n")

def norm_domain(domain):
    if not domain.endswith('.'):
        domain = '{}{}'.format(domain, '.')
    return domain

def norm_hostname(hostname):
    if hostname.endswith('.'):
        hostname = hostname[0:-1]
    return hostname

def get_all_running_instances():
    '''Get all active instances that have names and their primary internal ip address.
    '''
    instances = dict()
    instances = [ {'Name': i.tags['Name'], 'ip': i.private_ip_address} for res in ec2conn.get_all_instances()
                    for i in res.instances if i.state == 'running' and 'Name' in i.tags and i.tags['Name']
                ]
    return instances

def instances_for_appsgroup(instances, appsgroup):
    # only instances from the subnet, assuming they are named 'hostname-appsgroup'
    instances = [ i for i in instances if i['Name'].endswith('-{}'.format(appsgroup)) ]
    return instances
    


class ec2DNSstate(object):
    def __init__(self, appsgroup, domain):
        self.domain = domain
        self.instances = get_all_running_instances()
        self.instances = instances_for_appsgroup(self.instances, appsgroup)

    def __repr__(self):
        return self.__dict__.__repr__()

    def update(self):
        for i in self.instances:
            print('Adding {} with ip {} to {}'.format(i['Name'], i['ip'], self.domain))
            u = update_route53.DNSUpdater(self.domain, i['Name'], i['ip'])
            u.update()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Assuming instances are named name-appsgroup, this script updates Route53 with hostnames and private ips.",
        epilog="""This scripts requires AWS_SECURITY_TOKEN and AWS_ACCESS_KEY_ID.
        AWS_DEFAULT_REGION can be used to set a different region.
        """,
        )
    parser.add_argument("appsgroup", help="Name of the applications group, e.g.: \"qa5\"")
    parser.add_argument("domain", help="Name of the domain the hosts will be added to, e.g.: \"customername.outpace.com\"")
    args = parser.parse_args()

    runit = ec2DNSstate(**vars(args))
    runit.update()

