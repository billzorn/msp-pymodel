#!/bin/bash

for TRFILE in "$1"/*.json; do
    CMD="7z a -si $TRFILE.7z -t7z -mx=9"
    echo $CMD
    time $CMD < $TRFILE
done
