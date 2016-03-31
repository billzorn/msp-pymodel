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
ELFPATH="$SCRATCH/sloaded.elf"
ASMPATH="$SCRATCH/sloaded.asm"

MSPTOOLS="/home/bill/private/tools/msp430-gcc-linux32"
MSPGCC="$MSPTOOLS/bin/msp430-elf-gcc -nostdlib -T$MSPTOOLS/include/msp430fr5969.ld"
MSPOBJDUMP="$MSPTOOLS/bin/msp430-elf-objdump"

$MSPGCC $SPATH -o $ELFPATH
$MSPOBJDUMP -D $ELFPATH > $ASMPATH

MSPINIT="$SCRATCH/sloaded.mspdebug"
echo "prog $ELFPATH" > $MSPINIT

rlwrap mspdebug tilib -q -C $MSPINIT
