
# Should work both with python2 and python3

import json
import http.client
import urllib.parse
import logging


def trigger_event(service_key=None, description=None, incident_key=None, client=None, client_url=None, details=None):
    pg_url = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'
    pg_payload = dict()
    pg_payload['event_type'] = 'trigger'

    pg_payload['service_key'] =  service_key
    pg_payload['description'] = description
    pg_payload['incident_key'] =  incident_key
    pg_payload['client'] = client
    pg_payload['details'] = details # should be a dictionary

    # remove all None values
    pg_payload = { k: v for k,v in pg_payload.items() if v }

    pg_json = json.dumps(pg_payload)
    logging.debug(pg_json)

    pg_url_split = urllib.parse.urlsplit(pg_url)
    logging.warning('sending alert to pager duty')
    pg_conn = http.client.HTTPSConnection(pg_url_split.netloc)
    pg_conn.request('POST', pg_url_split.path, pg_json)
    pg_response = pg_conn.getresponse()
    # If this fail, there isn't much more we can do, but let's log it
    logging.warning(pg_response.status)
    if pg_response.status != 200:
        logging.warning(pg_response.read())

