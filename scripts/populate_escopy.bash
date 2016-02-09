#!/bin/bash -e


exec 1>/var/tmp/populate_escopy.$$.out
exec 2>&1


echo -e "\nstarted:" $(date) "\n\n"
/etc/init.d/elasticsearch stop

pathdata=$(grep '^path\.data' /etc/elasticsearch/elasticsearch.yml | awk '{print $2}')
clustername=$(grep '^cluster\.name' /etc/elasticsearch/elasticsearch.yml | awk '{print $2}')

indicespath=${pathdata}/${clustername}/nodes/0/indices
[[ ! -d $indicespath ]] && mkdir -p $indicespath
chown -R elasticsearch:elasticsearch ${pathdata}

allindices=()
for d in /media/*/elastic/prod/nodes/*/indices/*
do
    if [[ $(ls $d |grep -v _state |wc -l) -ne 0 && !($d =~ guests*) ]] ; then
        allindices[${#allindices[*]}]="$d"
    fi
done

for index in "${allindices[@]}"
do
    for source in $(find $index)
    do
        if [ -d $source ] ; then
            subdir=${source##*/indices/}
            echo subdir: $subdir
            [ ! -d ${indicespath}/$subdir ] && mkdir -p ${indicespath}/$subdir
        else
            filename=${source##*/}
            subdir=${source##*/indices/}
            subdir=${subdir%/*}
            [ ! -d ${indicespath}/$subdir ] && mkdir -p ${indicespath}/$subdir
            cp $source ${indicespath}/${subdir}/. &
            echo subdir: $subdir filename: $filename
        fi
    done
done

echo -e "\nWaiting for the copies to be terminated...\n"
while [ $(jobs |wc -l) -ne 0 ]
do
    # quantum scripting... if you don't look it hasn't happened
    jobs >/dev/null
    sleep 2
done

chown -R elasticsearch:elasticsearch ${pathdata}
echo -e "\nTerminated:" $(date) "\n\n"
