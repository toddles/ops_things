#!/bin/bash -e

# Compresses the logs
#
# Look for file names with pattern yyyymmdd, yyyy-mm-dd etc...
# We have to use a somewhat fuzzy pattern as the log files come with
# the date attached, the date split with dashes, the word 'log' before the
# date, or after!
#
# We asssume that:
#  - there are always two digits for the month and the day.
#  - no space in the filename
# 
# We do not compress a file with today's or yesterday's date in it.
#

TOPDIR=/sitelogs
COMPRESS='lzip -9'
THISSCRPT=$(basename $0)
LOCKFILE=${TOPDIR}/${THISSCIRPT}.lock

# Be as inconspicuous as possible
my_pid=$$
echo $my_pid
renice -n 40 -p $my_pid
ionice -n3 -p $my_pid

(
flock -n 22 || exit 0

todayy=$(date +"%Y") ; todaym=$(date +"%m") ; todayd=$(date +"%d")
yesterdayy=$(date -d yesterday +"%Y")
yesterdaym=$(date -d yesterday +"%m")
yesterdayd=$(date -d yesterday +"%d")

# bash can do lists!
#                       y   y    y    y          m    m          d     d 
for filename in $(find ${TOPDIR} 2>/dev/null \
               |grep -v 'gz$' \
               |grep -v 'lz$' \
               |egrep '[12][90][0-9][0-9][-_.]?[01]?[0-9][-_.]?[0-3]?[0-9]' \
               |egrep -v "${todayy}[-_.]?${todaym}[-_.]?${todayd}" \
               |egrep -v "${yesterdayy}[-_.]?${yesterdaym}[-_.]?${yesterdayd}" \
                 )
  do
  ${COMPRESS} $filename &
  cpulimit -l 49 -z -p $!
  done
) 22>${LOCKFILE}


