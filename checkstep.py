#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

import sys
import os

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
    
    recent_io = mulator.iotrace2[-1]
    for addr, value in recent_io['w']['mem']:
        if ((model.ram_start <= addr and addr < model.ram_start + model.ram_size)
            or (model.fram_start <= addr and addr < model.fram_start + model.fram_size)):
            mems, diff = cosim.md(addr, 1)
            if len(diff) > 0:
                mismatch = True
                print('-- mem mismatch @ {:05x}, write to {:05x} --'.format(pc, addr))
                utils.explain_diff(diff)
                cosim.sync(master_idx, diff=diff)

    if mismatch:
        print('')

    # I think this will be easier than actually trying to fetch anything question mark?
    return pc

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: {:s} <ELF>'.format(sys.argv[0]))
        exit(1)

    fname = sys.argv[1]
    sync_every = 100

    # bring up cosim
    with MSPdebug(verbosity=0) as driver:
        mulator = Emulator(verbosity=0, tracing=True)
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
                diff = cosim.diff()
                if len(diff) > 0:
                    print('---- routine diff failed @ {:05x}, step {:d} ----'.format(pc, i))
                    utils.explain_diff(diff)
                    print('')
                    cosim.sync(master_idx, diff=diff)
        
