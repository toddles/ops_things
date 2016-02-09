#!/usr/bin/env python

from __future__ import print_function
import os
import re
import datetime
import sys


if len(sys.argv) != 2:
    txt = """
Missing name of the file to split.

usage: {} /path/to/big/log/file
Splits an nginx log into smaller files, one file per day. The original file
will not be modified. The new files are created in the current directory.

""".format(os.path.basename(sys.argv[0]))
    print(txt, file=sys.stderr)
    sys.exit(1)

input_file = sys.argv[1]
pattern_log = re.compile('\[(../.*?/....):')
pattern_err = re.compile('(^20[0-9][0-9]/[0-1][0-9]/[0-3][0-9])')

curr_date = None
output_file = None
input_file_name = os.path.basename(input_file)
with open(input_file) as f:
    for line in f:
        # log files are much bigger than error files, so order is important.
        r = pattern_log.search(line)
        if r:
            date_stamp = datetime.datetime.strptime(r.group(1), "%d/%b/%Y")
        else:
            r = pattern_err.search(line)
            if r is None:
                print(line)
            date_stamp = datetime.datetime.strptime(r.group(1), "%Y/%m/%d")

        date_stamp = datetime.date.isoformat(date_stamp)
        if date_stamp != curr_date:
            curr_date = date_stamp
            if output_file:
                output_file.close()
            output_file = open("{}-{}".format(input_file_name, date_stamp), "w")
        output_file.write(line)
    output_file.close()
    


