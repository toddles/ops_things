#!/usr/bin/python3

#  Requires the following Ubuntu packages (and auto-installed dependencies)
#  python3-botocore

import re
import sys
import time
import logging
import botocore.session

logging.basicConfig(format='%(asctime)sZ pid:%(process)s %(message)s', level=logging.INFO)


def get_ec2_instances(ec2):

    # Get the AWS keys from the environment
#    os.environ['AWS_ACCESS_KEY_ID'] = allvars['ebs_snapshot']['aws_access_key']
#    os.environ['AWS_SECRET_ACCESS_KEY'] = allvars['ebs_snapshot']['aws_secret_key']

    # Get a list of the instances in the account
    ec2_instances = [ y for x in ec2.describe_instances()['Reservations']
                            for y in x['Instances']
                    ]
    return ec2_instances


def get_volumes_to_snap(ec2_instances, args):
    volumes_to_snap = list()
    
    ip_clean = re.compile('\[/*(.*):')

    # Loop through the instances
    # Identify the instances where the Tag exists and the Value matches
    # Populate a list of volumes for those identified instances
    for instance in ec2_instances:
       try:
          #print(instance['Tags'])
          for inkey in instance['Tags']:
             if inkey['Key'] == args[1]:
               if inkey['Value'] == args[2]:
                  hostname = [ x['Value'] for x in instance['Tags'] if x['Key'] == 'Name' ][0]
                  #print(hostname)
                  #print(inkey['Value'])
                  #print(instance['BlockDeviceMappings'][0])
                  devices = instance['BlockDeviceMappings']
                  for device in devices:
                    #print(device['DeviceName'], device['Ebs']['VolumeId'])
                    volumes_to_snap.append({ 'Name': hostname, 'DeviceName': device['DeviceName'], 'VolumeID': device['Ebs']['VolumeId'] })
       except KeyError:
          # do nothing
          hostname = ""

    return volumes_to_snap


def snap_volumes(ec2, volumes_to_snap):
    
    #print(volumes_to_snap)

    # Loop through the list of volumes and instantiate a snapshot
    for v in volumes_to_snap:
        description = ' '.join([now, v['Name'], v['DeviceName']])
        #print(description)
        #print(v['VolumeID'])
        volid=v['VolumeID']
        logging.warning('starting snapshot for ' + str(v))

        # Retry create_snapshot 3 times in case of failure, sleeping 10 seconds between retry
        for snap_attempt in range(3):
           try:
              snapshot = ec2.create_snapshot(VolumeId=volid, Description=description)
           except:
              logging.warning('Create snapshot attempt failed, sleeping 10 seconds...')
              time.sleep(10)
           break

        # Retry create_tags 3 times in case of failure, sleeping 10 seconds in between retry
        for tag_attempt in range(3):
           try:
              ec2.create_tags(Resources=[snapshot['SnapshotId']], Tags=[{'Key': 'Name', 'Value': description},{'Key': 'created_by', 'Value': 'Outpace Auto-Snap Utility'}])
           except:
              logging.warning('Tag attempt failed, sleeping 10 seconds...')
              time.sleep(10)
           break
        logging.warning('Created and tagged snapshot id: ' + snapshot['SnapshotId'])


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("syntax: {} [AWS Tag Name] [AWS Tag Value]\ne.g.: {} Name \"Postgres SQL\"".format(sys.argv[0], sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    # Get all environment variables
    #allvars = python3libs.all_vars.get()

    # Initialize a boto session to AWS
    session = botocore.session.get_session()
    ec2 = session.create_client('ec2', region_name='us-west-2')

    # Get all EC2 instances from the account
    ec2_instances = get_ec2_instances(ec2=ec2)

    # Get all appropriate volumes to snapshot
    volumes_to_snap = get_volumes_to_snap(ec2_instances=ec2_instances, args=sys.argv)

    now = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    # Take a snapshot of each of the volumes in the list
    snap_volumes(ec2, volumes_to_snap)

    logging.warning('SUCCESSFUL.')
