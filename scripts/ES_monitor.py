#!/usr/bin/python3

# Requirements:
#   elasticsearch:
#       sudo aptitude install ipython3 pip3 python3-yaml
#       sudo pip3 install elasticsearch yaml

import sys
import time
import elasticsearch
import python3libs.all_vars
import python3libs.pager_duty
import logging

MAX_TRY_TO_CONNECT = 3

logging.basicConfig(format='%(asctime)sZ pid:%(process)s %(message)s', level=logging.INFO)




def pager_duty_event(text, service_key):
    python3libs.pager_duty.trigger_event(service_key = service_key,
                                         description = text,
                                         incident_key = text,
                                        )

def booleanize(text):
    """Return a bool True/False based on a case insensitive text value.

    Return True if a flush_is_disabled
    """
    ltext = text.lower()
    if ltext == 'true':
        booleanized = True
    elif ltext == 'false':
        booleanized = False
    else:
        raise ValueError('A monk asked: Is "{}" true or false.'.format(text))
    return booleanized

def check_translog_flush(es, service_key):
    logging.warning('\n')
    iterations = 36 # 36 * 5 = 3 minutes
    sleeptime = 5
    itdf = 'index.translog.disable_flush'
    counter = 0
    disabled = True
    while counter <= iterations:
        flush_settings = { k: booleanize(v['settings'][itdf]) for (k, v) in es.indices.get_settings().items() }
        for idx, settings in flush_settings.items():
            text = '"{}" for index "{}" is: {}'.format(itdf, idx, flush_settings[idx])
            logging.warning(text)
        # All translog.disable_flush should be False
        if any(flush_settings.values()):
            # sleep 5 seconds and check again
            counter += 1
            time.sleep(sleeptime)
        else:
            disabled = False
            break

    if disabled:
        text = '"{}" has been disabled for one of the index for about {} seconds.'.format(itdf, iterations * sleeptime)
        pager_duty_event(text, service_key)


def check_cluster_status(es, service_key):
    logging.warning('\n')
    es_status = es.cluster.health()['status']
    text = 'ElasticSearch status is: "{}"'.format(es_status)
    logging.warning(text)
    if es_status.lower() != 'green':
        pager_duty_event(text, service_key)

def check_routing_allocation(es, service_key):
    logging.warning('\n')
    es_settings = es.cluster.get_settings()
    allocation = 'cluster.routing.allocation.disable_allocation'
    for config in ['transient', 'persistent']:
          if allocation in es_settings[config]:
              val = es_settings[config][allocation]
              text = 'ElasticSearch "{}" setting "{}" is {}.'.format(config, allocation, val)
              logging.warning(text)
              if val == 'true':
                  pager_duty_event(text, service_key)

def check_replicas(es, service_key):
    logging.warning('\n')
    idx_settings = { k: v['settings'] for (k, v) in es.indices.get_settings().items() }
    for idx, settings in idx_settings.items():
        replicas = int(settings['index.number_of_replicas'])
        s = ''
        if replicas > 1:
            s = 's'
        text = 'index {} has {} replica{}'.format(idx, replicas, s)
        logging.warning(text)
        if replicas < 1:
            pager_duty_event(text, service_key)





if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("syntax: {} url_of_ES_cluster\ne.g.: {} 172.31.20.192:9200".format(sys.argv[0], sys.argv[0]), file=sys.stderr)
        sys.exit(1)

    escluster = sys.argv[1]
    allvars = python3libs.all_vars.get()
    service_key=allvars['pager_duty']['ElasticSearch_monitors_service_key']
    tried_to_connect = 1

    functions_to_check = [ check_cluster_status,
                           check_routing_allocation,
                           check_replicas,
                           check_translog_flush,
                         ]
    while True:
        try:
            logging.warning("connecting to {} ({}th time)".format(escluster, tried_to_connect))
            es = elasticsearch.Elasticsearch(escluster)

            logging.warning('ES monitor started.')

            for funct in functions_to_check:
                funct(es, service_key)

            logging.warning('\n')
            logging.warning('ES monitor run complete.')

            break
        except elasticsearch.TransportError:
            # too many false positive. We now try to connect a few times before crying wolf
            if tried_to_connect < MAX_TRY_TO_CONNECT:
                tried_to_connect += 1
                logging.warning("going to sleep for two seconds.")
                time.sleep(2)
            else:
                text = 'The "{}" script was unable to contact {}.'.format(sys.argv[0].split('/')[-1], escluster)
                pager_duty_event(text, service_key)
                raise




