#!/bin/bash

for FILE in "$1"/*"$2"; do
    CMD="ln -s $FILE ."
    echo $CMD
    $CMD
done
