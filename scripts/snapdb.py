#!/usr/bin/python3

# Requirements:
#   elasticsearch:
#       sudo aptitude install ipython3 pip3 python3-yaml
#       sudo pip3 install elasticsearch yaml

import os
import re
import sys
import time
import json
import yaml
import time
import botocore.session
import os.path
import http.client
import urllib.parse
import elasticsearch
import python3libs.all_vars
import python3libs.pager_duty
import logging

logging.basicConfig(format='%(asctime)sZ pid:%(process)s %(message)s', level=logging.INFO)



def get_ec2_instances(allvars, ec2):
    os.environ['AWS_ACCESS_KEY_ID'] = allvars['ebs_snapshot']['aws_access_key']
    os.environ['AWS_SECRET_ACCESS_KEY'] = allvars['ebs_snapshot']['aws_secret_key']
    ec2_instances = [ y for x in ec2.describe_instances()['Reservations']
                            for y in x['Instances']
                    ]
    return ec2_instances


def get_volumes_to_snap(ec2_instances, es):
    # ES cluster nodes
    volumes_to_snap = list()
    esnodes = es.nodes.info()['nodes']
    ip_clean = re.compile('\[/*(.*):')
    for nodeid in esnodes:
        # http_address is formatted as 'inet[/172.31.20.100:9200]'
        esnodes[nodeid]['http_address'] = ip_clean.search(esnodes[nodeid]['http_address']).group(1)
        esnodes[nodeid]['dev'] = [ {'dev': fs['dev'], 'mount': fs['mount']} for fs in es.nodes.stats(nodeid, 'fs')['nodes'][nodeid]['fs']['data'] ]
        esnodes[nodeid]['ec2'] = [ x for x in ec2_instances
                                     if x['State']['Name'] == 'running'
                                     and x['PrivateIpAddress'] == esnodes[nodeid]['http_address']
                                 ]
        esnodes[nodeid]['ec2'] = esnodes[nodeid]['ec2'][0]
        hostname = [ x['Value'] for x in esnodes[nodeid]['ec2']['Tags'] if x['Key'] == 'Name' ][0]

        # We compare the two last letters of the device names
        # because some devices appear as /dev/sdf in ec2 API, but mount as /dev/xvdf

        for v in esnodes[nodeid]['dev']:
            for d in esnodes[nodeid]['ec2']['BlockDeviceMappings']:
                if d['DeviceName'][-2:] == v['dev'][-2:]:
                    volumes_to_snap.append({ 'Name': hostname, 'mount': v['mount'], 'VolumeId': d['Ebs']['VolumeId'] })
    return volumes_to_snap



def es_disable_flush(es):
    # do the work: disbale auto-flush, manually flush, do the snapshots
    logging.warning('disable translog flush on all indices')
    result = es.indices.put_settings({"index.translog.disable_flush": True})
    if not result['ok']:
        raise RuntimeError("setting index.translog.disable_flush did not return ok", result)


def es_flush(es):
    logging.warning('start flushing all indices')
    result = es.indices.flush()
    if result['_shards']['failed'] > 0 or not result['ok']:
        raise RuntimeError("Got error when trying to flush", result)
    logging.warning('all indices flushed')


def snap_volumes(ec2, volumes_to_snap):
    for v in volumes_to_snap:
        description = ' '.join([now, v['Name'], v['mount']])
        logging.warning('starting snapshot for ' + str(v))
        snapshot = ec2.create_snapshot(VolumeId=v['VolumeId'], Description=description)
        ec2.create_tags(Resources=[snapshot['SnapshotId']], Tags=[{'Key': 'Name', 'Value': description},{'Key': 'created_by', 'Value': 'Outpace Auto-Snap Utility'}])
        logging.warning('Created and tagged snapshot id: ' + snapshot['SnapshotId'])



def es_enable_flush(es, allvars):
    # re-enable auto-flush
    # try a bunch of times (8 times over 4.25 minutes (an engineering minute?))
    # alert if fails
    waittime = 0
    counter = 0
    success = False
    while  waittime < 130 and not success:
        if waittime > 0:
            # failure happend
            logging.warning('Failed! Going to sleep for {} seconds before new attempt.'.format(waittime))
            time.sleep(waittime)
            waittime *= 2
        else:
            # first loop
            waittime = 1

        counter += 1
        logging.warning('re-enable translog flush on all indices - iteration: {}'.format(counter))
        result = es.indices.put_settings({"index.translog.disable_flush": False})
        if result['ok']:
            success = True
            logging.warning('translog flush re-enabled.')
            break

    if not success:
        send_pager_duty_alert(allvars)
        raise RuntimeError("Could not re-enable flush. A alert has been sent to pager duty.")



def send_pager_duty_alert(allvars):
    description = 'FAILURE to re-enable ElasticSearch Flush'

    details = dict()
    details['issue'] = description
    details['help'] = 'Run the enable command and the verify command on a node of the cluster (remove the backslashes)'
    details['verify command'] = 'curl -s localhost:9200/_cluster/state?pretty |grep flush'
    details['enable command'] = 'curl -s -XPUT localhost:9200/_settings?pretty -d \'{"index": {"translog.disable_flush": false}}\''

    python3libs.pager_duty.trigger_event(service_key = allvars['pager_duty']['ES_flush_service_key'],
                                        description = description,
                                        incident_key = description, 
                                        details = details,
                                       )


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("syntax: {} url_of_ES_cluster\ne.g.: {} 172.31.20.192:9200".format(sys.argv[0], sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    escluster = sys.argv[1]
    allvars = python3libs.all_vars.get()

    # Initialize a boto session to AWS
    session = botocore.session.get_session()
    ec2 = session.create_client('ec2', region_name='us-west-2')
                
    es = elasticsearch.Elasticsearch(escluster)

    ec2_instances = get_ec2_instances(allvars=allvars, ec2=ec2)
    volumes_to_snap = get_volumes_to_snap(ec2_instances=ec2_instances, es=es)
    del ec2_instances

    now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    try:
        es_disable_flush(es)
        es_flush(es)
        snap_volumes(ec2, volumes_to_snap)
    finally:
        es_enable_flush(es, allvars)

    logging.warning('SUCCESSFUL.')



