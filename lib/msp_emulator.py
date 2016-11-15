# msp430 emulator

import utils
import msp_base as base
import msp_fr5969_model as model
import msp_peripheral_timer as peripheral_timer
import msp_reference_timing as reference_timing
import msp_elftools as elftools
import smt
from msp_isa import isa

class Emulator(object):
    def __init__(self, tracing = False, tinfo = None, verbosity = 0):
        self.tracing = tracing
        self.trace = []
        self.iotrace = model.iotrace_init()
        self.iotrace2 = []
        self.verbosity = verbosity

        if tracing:
            self.state = model.Model(trace=self.iotrace)
        else:
            self.state = model.Model()

        if tinfo is None:
            self.timing = False
            self._mmio_default()
        elif tinfo == 'reference':
            self.timing = True
            self._timer_default()
            self.timer_state_default = None
            self.timer_ttab = []
            self.timer_stab = []
            self._timer_reset()
        else:
            self.timing = True
            self._timer_default()
            self.timer_state_default = tinfo['state_default']
            self.timer_ttab = tinfo['ttab']
            self.timer_stab = tinfo['stab']
            self._timer_reset()

        if self.verbosity >= 3:
            print('created {:s}'.format(str(self)))
            self.state.dump()

    def _mmio_default(self):
        # watchdog (unimplemented)
        for addr in [0x15c, 0x15d]:
            self.state.mmio_handle_default(addr)
        # timerA (unimplemented)
        for addr in [0x0340, 0x0341, 0x0342, 0x0343, 0x0350, 0x0351, 0x0352, 0x0353]:
            self.state.mmio_handle_default(addr)

    def _timer_default(self):
        # watchdog (unimplemented)
        for addr in [0x15c, 0x15d]:
            self.state.mmio_handle_default(addr)
        # call out to timer module
        self.timer_A = peripheral_timer.Peripheral_Timer()
        self.timer_A.attach_timer(self.state, peripheral_timer.timer_A_base)

    def _timer_reset(self):
        self.timer_cycles = 0
        self.timer_state = self.timer_state_default

    def _timer_update(self, ins, fields):
        # cycles = None
        # iname = smt.smt_iname(ins)
        # if (self.timer_state, iname, None, None) in self.timer_ttab:
        #     assert cycles is None
        #     cycles = self.timer_ttab[(self.timer_state, iname, None, None)]
        #     assert cycles is not None
        # rsname = smt.smt_rsrc(fields)
        # if (self.timer_state, iname, rsname, None) in self.timer_ttab:
        #     assert cycles is None
        #     cycles = self.timer_ttab[(self.timer_state, iname, rsname, None)]
        #     assert cycles is not None
        # rdname = smt.smt_rdst(fields)
        # if (self.timer_state, iname, None, rdname) in self.timer_ttab:
        #     assert cycles is None
        #     cycles = self.timer_ttab[(self.timer_state, iname, None, rdname)]
        #     assert cycles is not None
        # if (self.timer_state, iname, rsname, rdname) in self.timer_ttab:
        #     assert cycles is None
        #     cycles = self.timer_ttab[(self.timer_state, iname, rsname, rdname)]
        #     assert cycles is not None
        # assert cycles is not None and cycles >= 0
        # self.timer_state = self.timer_stab[self.timer_state, iname]
        
        if self.timer_ttab or self.timer_stab:
            iname = smt.smt_iname(ins)
            rsname = smt.ext_smt_rsrc(fields)
            rdname = smt.ext_smt_rdst(fields)

            cycles = self.timer_ttab[self.timer_state, iname, rsname, rdname]

            if cycles is None and (ins.name in {'BIC', 'BIS'} and
                                   ins.smode in {'@Rn', '@Rn+'} and
                                   ins.dmode in {'Rn'} and
                                   rsname in {smt.smt_rnames[2], smt.smt_rnames[3]} and
                                   rdname in {smt.smt_rnames[2]}):
                cycles = 1

            if cycles is None:
                raise base.UnknownBehavior('missing timer entry for {:d} {:s} {:s} {:s}'
                                           .format(self.timer_state, iname, rsname, rdname))
            new_state = self.timer_stab[self.timer_state, iname, rsname, rdname]

            if new_state is None and (ins.name in {'BIC', 'BIS'} and
                                   ins.smode in {'@Rn', '@Rn+'} and
                                   ins.dmode in {'Rn'} and
                                   rsname in {smt.smt_rnames[2], smt.smt_rnames[3]} and
                                   rdname in {smt.smt_rnames[2]}):
                new_state = 0

            if new_state is None:
                raise base.UnknownBehavior('missing timer state transition for {:d} {:s} {:s} {:s}'
                                           .format(self.timer_state, iname, rsname, rdname))
        else:
            # use reference
            cycles = reference_timing.reference_time(ins, fields)
            new_state = self.timer_state_default

        self.timer_state = new_state
        self.timer_cycles = self.timer_cycles + cycles
        return cycles

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
                print(utils.describe_regs(self.regs()))
                ins.describe()
                utils.print_dict(fields)

        ins.execute(fields)
        ins.writefields(self.state, fields)

        # remember the thing we just added to our iotrace, and make a dummy to intercept
        # non-execution IO before the next instruction
        if self.tracing:
            self.iotrace2.append(self.iotrace[-1])
            model.iotrace_next(self.iotrace)


            # # manual breakpoints / watchpoints

            # step_io = self.iotrace2[-1]
            # for addr, value in step_io['w']['mem']:
            #     if addr >= 0xfffe:
            #         print(hex(pc))
            #         utils.print_dict(step_io)
            #         raise base.Breakpoint('manual')

            # if pc == 0xfe84:
            #     print(hex(pc))
            #     raise base.Breakpoint('manual')

            # # end

        # update the timer if we're doing that
        if self.timing:
            cycles = self._timer_update(ins, fields)
            self.timer_A.elapse(cycles)

        if self.tracing and self.verbosity >= 2:
            print('----')

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
            if self.verbosity >= 0:
                print('Execution Error: {:s}'.format(str(e)))
            success = False
        except base.UnknownBehavior as e:
            if self.verbosity >= 0:
                print('Unknown Behavior: {:s}'.format(str(e)))
            success = False
        except base.Breakpoint as e:
            if self.verbosity >= 0:
                print('Breakpoint: {:s}'.format(str(e)))
            success = True
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

    success, steps = mulator.run(max_steps = 100000)
    print('Success: {}, steps: {:d}'.format(success, steps))

    print(len(mulator.trace))
    print(len(mulator.iotrace2))

    if not outname is None:
        mulator.save(outname)
