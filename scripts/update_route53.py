#!/usr/bin/env python

from __future__ import print_function
import sys
import argparse
import boto.route53


try:
    r53conn = boto.route53.connection.Route53Connection()
except boto.exception.NoAuthHandlerFound:
    print("\n\n\n     AWS_SECURITY_TOKEN and AWS_ACCESS_KEY_ID are either invalid or not set.\n\n\n")
default_ttl = 300

def norm_domain(domain):
    if not domain.endswith('.'):
        domain = '{}{}'.format(domain, '.')
    return domain

def norm_hostname(hostname):
    if hostname.endswith('.'):
        hostname = hostname[0:-1]
    return hostname

def get_records_for_a(all_records, ipaddr):
    return [ x for x in all_records if x.type == u'A' and ipaddr in x.resource_records ]

def remove_other_a_recs(zone, a_records, fqdn):
    '''Remove all A records that are not this fqdn
    '''
    to_delete = [ x.name for x in a_records if x.name != fqdn ]
    map(zone.delete_a, to_delete)

def check_hostname_in_domain(all_records, fqdn):
    there = [ x.name for x in all_records if x.name == fqdn ]
    there = True if there else False
    return there


class DNSUpdater(object):
    def __init__(self, domain, hostname, ipaddr, ttl=None):
        if not ttl:
            ttl = default_ttl
        self.ttl = ttl
        self.ipaddr = ipaddr
        self.domain = norm_domain(domain)
        self.hostname = norm_hostname(hostname)
        self.fqdn = '{}.{}'.format(self.hostname, self.domain)

        self.zone = r53conn.get_zone(domain)
        self.all_records = self.zone.get_records()
        self.a_rec_for_hostname = get_records_for_a(self.all_records, self.ipaddr)
        remove_other_a_recs(self.zone, self.a_rec_for_hostname, self.fqdn)
        self.exists = check_hostname_in_domain(self.all_records, self.fqdn)

    def __repr__(self):
        return self.__dict__.__repr__()

    def update(self):
        if self.exists:
            self.zone.update_a(self.fqdn, self.ipaddr, ttl=self.ttl)
        else:
            self.zone.add_a(self.fqdn, self.ipaddr, ttl=self.ttl)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add an A record to a specified DNS domain.",
        epilog="WARNING: THIS SCRIPT WILL REMOVE ALL EXISTING RECORDS WITH THE SAME IP.",
        )
    parser.add_argument("domain", help="DNS domain to be added to.")
    parser.add_argument("hostname", help="Name of this host.")
    parser.add_argument("ipaddr", help="IP address of this host.")
    parser.add_argument("--ttl", help="Ttl for new A records. Default: {} s.".format(default_ttl))
    args = parser.parse_args()

    updater = DNSUpdater(**vars(args))
    updater.update()

