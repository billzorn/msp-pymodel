#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

import sys
import os
import pickle

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import utils
import msp_fr5969_model as model
from mspdebug_driver import MSPdebug
from msp_emulator import Emulator
from msp_cosim import Cosim
import cosim as cosim_repl

def step_and_sync(cosim, maxter_idx, mulator):
    regvals, regdiff = cosim.regs()
    assert(len(regdiff) == 0)
    pc = regvals[master_idx][0]
    mismatch = False

    cosim.step()

    # checking registers is cheap
    regvals, regdiff = cosim.regs()
    if len(regdiff) > 0:
        mismatch = True
        print('-- register mismatch @ {:05x} --'.format(pc))
        utils.explain_diff(regdiff)
        cosim.sync(master_idx, diff={'regs':regdiff})

        # check timer state if we have a timer, just for kicks...
        if mulator.timing:
            mems, diff = cosim.md(0x0350, 2)
            if len(diff) > 0:
                # mismatch = True
                # print('-- timer mismatch @ {:05x} --'.format(pc))
                # utils.explain_diff(diff)
                cosim.sync(master_idx, diff=diff)

    recent_writes = mulator.iotrace2[-1]['w']['mem']
    for addr, value in recent_writes:
        if ((model.ram_start <= addr and addr < model.ram_start + model.ram_size)
            or (model.fram_start <= addr and addr < model.fram_start + model.fram_size)):
            # merge into word writes
            size = 1
            descr = 'byte'
            if addr % 2 == 0 and addr + 1 in recent_writes:
                size = 2
                descr = 'word'
            elif addr % 2 == 1 and addr - 1 in recent_writes:
                continue
            mems, diff = cosim.md(addr, size)
            if len(diff) > 0:
                mismatch = True
                print('-- mem mismatch @ {:05x}, {:s} write to {:05x} --'.format(pc, descr, addr))
                utils.explain_diff(diff)
                cosim.sync(master_idx, diff=diff)

    if mismatch:
        print('')

    # I think this will be easier than actually trying to fetch anything question mark?
    return pc

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: {:s} <ELF> <TTY> [MODEL]'.format(sys.argv[0]))
        exit(1)

    fname = sys.argv[1]
    tty = sys.argv[2]
    if len(sys.argv) >= 4:
        tname = sys.argv[3]

    if tname:
        with open(tname, 'rb') as f:
            tinfo = pickle.load(f)
    else:
        tinfo = None

    sync_every = 100

    # bring up cosim
    with MSPdebug(tty=tty, verbosity=0) as driver:
        mulator = Emulator(verbosity=0, tracing=True, tinfo=tinfo)
        mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
        cosim = Cosim([driver, mulator], [True, False], mmap)
        master_idx = 0

        cosim_repl.prog_and_sync(cosim, master_idx, fname)
        
        old_pc = None
        pc = step_and_sync(cosim, master_idx, mulator)
        i = 0

        while pc != old_pc:
            old_pc = pc
            pc = step_and_sync(cosim, master_idx, mulator)
            i += 1
            if i % sync_every == 0:
                
                print('doing diff @ {:05x}, step {:d}'.format(pc, i))

                diff = cosim.diff()
                if len(diff) > 0:
                    print('---- routine diff failed @ {:05x}, step {:d} ----'.format(pc, i))
                    utils.explain_diff(diff)
                    print('')
                    cosim.sync(master_idx, diff=diff)

                    # diff2 = cosim.diff()
                    # if len(diff2) > 0:
                    #     print('-- diff not fixed? --')
                    #     utils.print_dict(diff)
                    #     exit(0)
