#!/bin/bash

for PREF in "$@"; do
    CMD="./trace.py m5/d2/ -jo m5/blocks_d2_$PREF.json -trprefix $PREF -v 2"
    echo $CMD
    $CMD > m5/blocks_d2_$PREF.log
done
