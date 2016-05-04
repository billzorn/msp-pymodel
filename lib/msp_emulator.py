# msp430 emulator

import utils
import msp_base as base
import msp_fr5969_model as model
import msp_elftools as elftools
from msp_isa import isa

class Emulator(object):
    def __init__(self, tracing = False, verbosity = 0):
        self.tracing = tracing
        self.trace = []
        self.iotrace = model.iotrace_init()
        self.iotrace2 = []
        self.verbosity = verbosity

        if tracing:
            self.state = model.Model(trace=self.iotrace)
        else:
            self.state = model.Model()

        if self.verbosity >= 3:
            print('created {:s}'.format(str(self)))
            self.state.dump()
    
    def reset(self):
        reset_pc = model.mk_read16(self.state.read8)(model.resetvec)
        self.state.writereg(0, reset_pc)

    def load(self, fname, restore_regs = True):
        if self.verbosity >= 1:
            print('programming {:s}'.format(fname))
        elftools.load(self.state, fname, restore_regs=restore_regs, verbosity=self.verbosity)

    def save(self, fname):
        if self.verbosity >= 1:
            print('saving {:s}'.format(fname))
        elftools.save(self.state, fname, verbosity=self.verbosity)

    def prog(self, fname):
        self.fill(model.fram_start, model.fram_size, [0xff])
        self.load(fname)
        self.reset()

    def mw(self, addr, pattern):
        # print('emulator invoking mw {:05x} '.format(addr), utils.makehex(pattern))
        for i in range(len(pattern)):
            self.state.write8(addr + i, pattern[i])
        # utils.printhex([self.state.read8(i) for i in range(addr, addr+len(pattern))])

    def fill(self, addr, size, pattern):
        for i in range(size):
            self.state.write8(addr + i, pattern[i%len(pattern)])

    def setreg(self, register, value):
        self.state.writereg(register, value)

    def md(self, addr, size):
        # print('emulator invoking md {:05x} {:d}'.format(addr, size))
        memreads = [self.state.read8(i) for i in range(addr, addr+size)]
        # utils.printhex(memreads[:16])
        return memreads

    def regs(self):
        return [self.state.readreg(i) for i in range(len(self.state.regs))]

    def step(self):
        pc = self.state.readreg(0)
        word = model.mk_read16(self.state.read8)(pc)
        ins = isa.decode(word)
        
        if ins is None:
            raise base.ExecuteError('failed to decode {:#04x} ( PC: {:05x})'.format(word, pc))

        # TODO: iotrace should probably work in a reasonable way
        # right now we have two lists of io traces, one which includes all io, even not
        # from instruction execution, and a second one in self.iotrace2 which is only
        # io events from actually executing instructions
        if self.tracing:
            model.iotrace_next(self.iotrace)

        fields = ins.readfields(self.state)

        if self.tracing:
            self.trace.append(fields)
            if self.verbosity >= 2:
                print('\npc: {:05x}'.format(pc))
                ins.describe()
                utils.print_dict(fields)

        ins.execute(fields)
        ins.writefields(self.state, fields)

        # remember the thing we just added to our iotrace, and make a dummy to intercept
        # non-execution IO before the next instruction
        if self.tracing:
            self.iotrace2.append(self.iotrace[-1])
            model.iotrace_next(self.iotrace)

        if word == 0x3fff:
            # halt
            return False
        else:
            return True
            
    def run(self, max_steps = 0):
        steps = 0
        try:
            while self.step():
                steps += 1
                if max_steps > 0 and steps >= max_steps:
                    break
            success = True
        except base.ExecuteError as e:
            if self.verbosity >= 1:
                print('Execution Error: {:s}'.format(str(e)))
            success = False
        except base.UnknownBehavior as e:
            if self.verbosity >= 1:
                print('Unknown Behavior: {:s}'.format(str(e)))
            success = False
        else:
            success = True
        return success, steps

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('usage: {:s} <ELF>'.format(sys.argv[0]))
        exit(1)

    fname = sys.argv[1]
    if len(sys.argv) >= 3:
        outname = sys.argv[2]
    else:
        outname = None

    mulator = Emulator(tracing=True, verbosity=2)
    mulator.prog(fname)

    success, steps = mulator.run(max_steps = 10000)
    print('Success: {}, steps: {:d}'.format(success, steps))

    print(len(mulator.trace))
    print(len(mulator.iotrace2))

    if not outname is None:
        mulator.save(outname)
