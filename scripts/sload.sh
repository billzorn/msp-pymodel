#!/bin/bash

SPATH="$1"
if [ -z "$SPATH" ]; then
    echo "usage: $0 <ASM FILE>"
    exit 1
fi

#http://stackoverflow.com/questions/59895/can-a-bash-script-tell-what-directory-its-stored-in
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

SCRATCH="$DIR/scratch"
ELFPATH="$SCRATCH/assembled.elf"
ASMPATH="$SCRATCH/assembled.asm"

$DIR/assemble.sh $SPATH

MSPINIT="$SCRATCH/sloaded.mspdebug"
echo "prog $ELFPATH" > $MSPINIT

rlwrap mspdebug tilib -q -C $MSPINIT
