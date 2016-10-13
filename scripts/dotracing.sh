#!/bin/bash

TARGETDIR="m8/cluster"

for PREF in "$@"; do
    CMD="./trace.py $TARGETDIR/d2/ -jo $TARGETDIR/blocks_d2_$PREF.json -trprefix $PREF -v 2"
    echo $CMD
    $CMD > "$TARGETDIR/blocks_d2_$PREF.log.txt"
done
