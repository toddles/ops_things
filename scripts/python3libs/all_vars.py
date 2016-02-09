
# requirement:
#  pip3 install pyaml

import os
import yaml
import logging

def get():
    all_yaml_file = "~/src/universe/configuration_management/group_vars/all.yaml"
    logging.debug('reading "{}"'.format(all_yaml_file))
    allvars = yaml.load(open(os.path.expanduser( all_yaml_file)))
    return allvars
