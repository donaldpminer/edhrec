#!/bin/bash

while :
do
  echo "starting tasks " `date`
  python dedup.py

  python mtgsalvation.py

  sh backup.sh staging.edhrec.com

  echo "done with tasks" `date`

  sleep 3600 # run every hour

done
