#!/bin/bash

while :
do
  echo "starting tasks " `date`
  python dedup.py


  echo "done with tasks" `date`

  sleep 3600 # run every hour

done
