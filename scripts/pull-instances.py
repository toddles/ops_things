#!/usr/bin/env python

# This is using the aws cli, run derp auth before using it.

import csv
import json
import shlex
import subprocess

cmd = shlex.split("aws ec2 describe-instances")
all = subprocess.check_output(cmd)
all = json.loads(all)

instances = list()
for sublist_of_inst in all['Reservations']:
    for this_instance in sublist_of_inst['Instances']:
        new_instance = dict()
        instances.append(new_instance)
        # If values are simple strings,
        # add name of keys you want in the list here
        for k in ['InstanceId', 'PrivateIpAddress']:
            new_instance[k] = this_instance[k]

        if 'Tags' in this_instance:
            for kv in this_instance['Tags']:
                new_instance[ kv['Key'] ] = kv['Value']
del(all)

## some instances can have different keys due to Tags
all_keys = { e for x in instances for e in x.keys() }
all_keys = tuple( sorted(all_keys) )

with open('instances.csv', 'wb') as csv_file:
    csv_writer = csv.DictWriter(csv_file, fieldnames=all_keys)
    csv_writer.writeheader()
    csv_writer.writerows(instances)

