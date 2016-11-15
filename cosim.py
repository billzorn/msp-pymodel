#!/usr/bin/env python3

# msp430fr5969 cosimulator repl

import sys
import os
import traceback

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import utils
import msp_fr5969_model as model
from mspdebug_driver import MSPdebug
from msp_emulator import Emulator
from msp_cosim import Cosim

def int_or_hex(s):
    try:
        return int(s)
    except:
        return int(s, 16)

def prompt():
    print('(cosim) ', end='')
    sys.stdout.flush()

def prog_and_sync(cosim, master_idx, fname):
    # force reset the ram
    cosim.fill(model.ram_start, model.ram_size, [0xff, 0x3f])
    cosim.prog(fname)
    # check if we need to fix up the state
    diff = cosim.diff()
    if len(diff) == 1 and 'regs' in diff:
        print('register mismatch on prog, correcting')
        cosim.sync(master_idx, diff=diff)
    elif len(diff) > 0:
        print('prog mismatch:')
        utils.explain_diff(diff)
        cosim.sync(master_idx, diff=diff)

def do_cmd(cosim, master_idx, cmd, args):
    if cmd in {'reset'}:
        cosim.reset()

    elif cmd in {'prog', 'p'}:
        try:
            fname = args[0]
            prog_and_sync(cosim, master_idx, fname)
        except Exception as e:
            print('prog <ELF>')
            raise e

    elif cmd in {'mw'}:
        try:
            addr = int_or_hex(args[0])
            pattern = [int_or_hex(s) for s in args[1:]]
            cosim.mw(addr, pattern)
        except Exception as e:
            print('mw <ADDR> <PATTERN>')
            raise e

    elif cmd in {'fill'}:
        try:
            addr = int_or_hex(args[0])
            size = int_or_hex(args[1])
            pattern = [int_or_hex(s) for s in args[2:]]
            cosim.fill(addr, size, pattern)
        except Exception as e:
            print('fill <ADDR> <SIZE> <PATTERN>')
            raise e

    elif cmd in {'set'}:
        try:
            register = int_or_hex(args[0])
            value = int_or_hex(args[1])
            cosim.setreg(register, value)
        except Exception as e:
            print('set <REGISTER> <VALUE>')
            raise e

    elif cmd in {'md', 'x'}:
        try:
            addr = int_or_hex(args[0])
            size = int_or_hex(args[1])
            mems, diff = cosim.md(addr, size)
            if len(diff) == 0:
                print(utils.triple_summarize(mems[master_idx], addr))
            else:
                print('-- master {:d} --'.format(master_idx))
                print(utils.triple_summarize(mems[master_idx], addr))
                print('')
                utils.explain_diff(diff)
        except Exception as e:
            print('md <ADDR> <SIZE>')
            raise e

    elif cmd in {'regs', 'reg'}:
        regvals, regdiff = cosim.regs()
        if len(regdiff) == 0:
            print(utils.describe_regs(regvals[master_idx]))
        else:
            diff = {'regs' : regdiff}
            utils.explain_diff(diff)

    elif cmd in {'step', 's'}:
        cosim.step()

    elif cmd in {'run', 'r'}:
        try:
            if len(args) >= 1:
                max_steps = int_or_hex(args[0])
            else:
                max_steps = 10000
            if len(args) >= 2:
                interval = float(args[1])
            else:
                interval = 0.5
            if len(args) >= 3:
                passes = int_or_hex(args[2])
            else:
                passes = 10
            cosim.run(max_steps=max_steps, interval=interval, passes=passes)
        except Exception as e:
            print('run [MAX_STEPS] [INTERVAL] [PASSES]')
            raise e

    elif cmd in {'diff'}:
        diff = cosim.diff()
        if len(diff) == 0:
            print('states agree!')
        else:
            utils.explain_diff(diff)

    elif cmd in {'sync'}:
        try:
            if len(args) >= 1:
                sync_idx = int_or_hex(args[0])
            else:
                sync_idx = master_idx
            diff = cosim.diff()
            if len(diff) == 0:
                print('states agree, not syncing')
            else:
                utils.explain_diff(diff)
                print('syncing drivers to {:d}'.format(sync_idx))
                cosim.sync(sync_idx, diff)

        except Exception as e:
            print('sync [SYNC_IDX]')
            raise e

    else:
        print('unknown command: {:s}'.format(cmd))

def repl(cosim, master_idx):
    prompt()
    for line in sys.stdin:
        cmdline = line.strip().split()
        if len(cmdline) == 0:
            prompt()
            continue
        cmd = cmdline[0]
        args = cmdline[1:]

        if cmd in {'exit', 'q'}:
            print('exiting')
            break

        try:
            do_cmd(cosim, master_idx, cmd, args)
        except Exception:
            traceback.print_exc()

        prompt()

def main(fname = None, emulate = False, tinfo = None, tty = None, verbosity = 1):
    mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
    mulator = Emulator(tracing=True, tinfo=tinfo, verbosity=verbosity)

    if emulate:
        cosim = Cosim([mulator], [False], mmap)
        master_idx = 0

        if not fname is None:
            prog_and_sync(cosim, master_idx, fname)

        repl(cosim, master_idx)

    else:
        with MSPdebug(tty=tty, verbosity=verbosity) as driver:
            cosim = Cosim([driver, mulator], [True, False], mmap)
            master_idx = 0

            if not fname is None:
                prog_and_sync(cosim, master_idx, fname)

            repl(cosim, master_idx)

    print('goodbye!')

if __name__ == '__main__':
    import subprocess
    import argparse
    import pickle
    parser = argparse.ArgumentParser()

    parser.add_argument('fname', nargs='?', default=None,
                        help='initial file to program on startup')
    parser.add_argument('-e', '--emulator', action='store_true',
                        help='run with emulator only')
    parser.add_argument('-t', '--timing',
                        help='use this pickled timing model to emulate Timer_A')
    parser.add_argument('-v', '--verbose', type=int, default=1,
                        help='verbosity level')
    parser.add_argument('-tty', default=None,
                        help='connect to mspdebug on this TTY')
    
    args = parser.parse_args()

    fname = args.fname
    if args.fname != None:

        # horrible horrible check if the file is executable
        with open(fname, 'rb') as f:
            if f.read(4) == b'\x7fELF':
                is_executable = True
            else:
                is_executable = False

        # horrible horrible assembler script
        if not is_executable:
            print('assembling...')
            script_dir = os.path.join(libdir, '../scripts')
            assembler = os.path.join(script_dir, 'assemble.sh')
            subprocess.check_call([assembler, args.fname])
            scratch_dir = os.path.join(script_dir, 'scratch')
            fname = os.path.join(scratch_dir, 'assembled.elf')

    if args.timing:
        if args.timing == 'reference':
            tinfo = 'reference'
        else:
            with open(args.timing, 'rb') as f:
                tinfo = pickle.load(f)
    else:
        tinfo = None

    main(fname=fname, emulate=args.emulator, tinfo=tinfo, tty=args.tty, verbosity=args.verbose)
    exit(0)
