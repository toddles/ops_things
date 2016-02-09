#!/bin/bash

#
# Try to ssh to a bunch of ip addresses, keeping track
# of successes and failures
#
this_script=$(basename $0)

if [[ $# -ne 2 ]] ; then
    echo "" >&2
    echo "usage: $this_script private_key list__of_addr.txt" >&2
    echo "" >&2
    echo "list_of_addr.txt is a text file listing ip addresses, one per line." >&2
    echo "Use the following command to populate list_of_addr.txt:" >&2
    echo "    aws ec2 describe-instances |grep PublicIp | cut -d\" -f4 |uniq >list_of_addr.txt" >&2
    echo "" >&2
    echo "Make sure you run \"ssh-add -D\" before you run the script." >&2
    echo "" >&2
    exit 1
fi

key=$1
ip_list=$2

for f in "$key" "$ip_list"
do
    if [[ ! -f "$f" ]] ; then
       echo "Cannot open $f" >&2
        exit 1
    fi
done

fail255=/tmp/${this_script}.fail.255
otherfail=/tmp/${this_script}.otherfail
success=/tmp/${this_script}.success

for f in "$fail255" "$otherfail" "$otherfail"
do
    if [[ -f $f ]] ; then
        echo "Please remove \"$f\" before running this script."
        exit 1
    fi
done

for ip in $(cat $ip_list)
do
    echo -n "checking ${ip}..."
    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $key ubuntu@$ip /bin/true >/dev/null 2>&1
    retcode=$?
    echo " $retcode"
    case $retcode in
      0) echo $ip >>$success ;;
      255) echo $ip >>$fail255 ;;
      *) echo $ip >>$otherfail
    esac
done

for f in $success $otherfail $fail255
do
    [[ -f $f ]] && wc -l $f
done

