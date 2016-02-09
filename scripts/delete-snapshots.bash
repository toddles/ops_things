#!/bin/bash

# don't forget to derp authenticate


if [[ -z $1 ]] ; then
    echo "usage: $(basename $0) 'pattern_to_delete'" >&2
    exit 1
fi

aws --output text ec2 describe-snapshots --filters Name=description,Values="$1"
read -p "Delete all the above snapshots (y/n)? "

if [[ "$REPLY" == [yY] ]] ; then
    for s in $(aws --output json ec2 describe-snapshots --filters Name=description,Values="$1" |grep SnapshotId |cut -d\" -f4)
        do
        echo "deleting snapshot $s"
        aws ec2 delete-snapshot --snapshot-id "$s"
        done
else
    echo Aborting...
fi
