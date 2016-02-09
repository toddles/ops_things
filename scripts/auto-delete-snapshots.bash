#!/bin/bash

. ${HOME}/.profile

# Will delete snapshots based upon the age of the snapshot.
# Assumes the description contains a date in the format YYYY-MM-DD

if [[ -z $1 ]] ; then
    echo "usage: $(basename $0) 'number of days to delete'" >&2
    exit 1
fi

# Get the date
for ((i=$1; i<=(($1+15)); i++)) {
   date_to_delete=$(date +%Y-%m-%d -d "$i days ago")
   #echo $date_to_delete
   date_to_delete="${date_to_delete}*"
   #echo $date_to_delete
   snap_filter="[{\"Name\":\"description\",\"Values\":[\"${date_to_delete}\"]},{\"Name\":\"tag:created_by\",\"Values\":[\"Outpace?Auto-Snap?Utility\"]}]"
   echo "$(date): Applying the following filter: ${snap_filter}"

   # Remove only snapshots created by the Auto-Snap Utility
   echo "$(date): Removing the following snapshots..."
   /usr/local/bin/aws --output text ec2 describe-snapshots --filters $snap_filter
   for s in $(/usr/local/bin/aws --output json ec2 describe-snapshots --filters $snap_filter |grep SnapshotId |cut -d\" -f4)
       do
       echo "$(date): Deleting snapshot $s"
       /usr/local/bin/aws ec2 delete-snapshot --snapshot-id "$s"
       done
   }
