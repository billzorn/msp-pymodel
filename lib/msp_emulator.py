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
        self.verbosity = verbosity
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
        self.load(fname)
        self.reset()

    def mw(self, addr, pattern):
        for i in range(len(pattern)):
            self.state.write8(addr + i, pattern[i])

    def fill(self, addr, size, pattern):
        for i in range(size):
            self.state.write8(addr + i, pattern[i%len(pattern)])

    def setreg(self, register, value):
        self.state.writereg(register, value)

    def md(self, addr, size):
        return [self.state.read8(i) for i in range(addr, addr+size)]

    def regs(self):
        return [self.state.readreg(i) for i in range(len(self.state.regs))]

    def step(self):
        pc = self.state.readreg(0)
        word = model.mk_read16(self.state.read8)(pc)
        ins = isa.decode(word)
        
        if ins is None:
            raise base.ExecuteError('failed to decode {:#04x} ( PC: {:05x})'.format(word, pc))

        fields = ins.readfields(self.state)

        if self.tracing:
            self.trace.append(fields)
            if self.verbosity >= 2:
                utils.print_dict(fields)

        ins.execute(fields)
        ins.writefields(self.state, fields)

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
        except base.ExecuteError as e:
            if self.verbosity >= 1:
                print('Execution Error: {:s}'.format(e))
            success = False
        except base.UnknownBehavior as e:
            if self.verbosity >= 1:
                print('Unknown Behavior: {:s}'.format(e))
            success = False
        else:
            success = True
        finally:
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

    if not outname is None:
        mulator.save(outname)
