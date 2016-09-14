# msp430 Timer_A emulator

import msp_base as base
import msp_fr5969_model as model

timer_A_base = 0x340
timer_mem_size = 48

class Peripheral_Timer(object):
    def __init__(self):
        self.mem = [0 for _ in range(timer_mem_size)]
        self.__read16 = model.mk_read16(self._read8)
        self.__write16 = model.mk_write16(self._write8)
        
    def _mk_read_handler(self, offset):
        def read_handler(v):
            return self.mem[offset]
        return read_handler

    def _mk_write_handler(self, offset):
        def write_handler(v):
            self.mem[offset] = v
            return
        return write_handler

    def attach_timer(self, state, base_addr):
        for i in range(len(self.mem)):
            read_handler = self._mk_read_handler(i)
            write_handler = self._mk_write_handler(i)
            addr = base_addr + i
            state.set_mmio_read_handler(addr, read_handler)
            state.set_mmio_write_handler(addr, write_handler)

    def _read8(self, idx):
        return self.mem[idx]

    def _write8(self, idx, v):
        self.mem[idx] = v
        return

    @property
    def TAxCTL(self):
        return self.__read16(0x0)
    @TAxCTL.setter
    def TAxCTL(self, v):
        self.__write16(0x0, v)
        return

    @property
    def TAxR(self):
        return self.__read16(0x10)
    @TAxR.setter
    def TAxR(self, v):
        self.__write16(0x10, v)
        return

    @property
    def TAxCCR0(self):
        return self.__read16(0x12)
    @TAxCCR0.setter
    def TAxCCR0(self, v):
        self.__write16(0x12, v)
        return

    def elapse(self, cycles):
        MC = (self.TAxCTL & 0x30) >> 4
        if MC == 1 or MC == 2:
            r = self.TAxR
            r += cycles
            if MC == 1:
                ccr0 = self.TAxCCR0
                if r >= ccr0:
                    raise base.UnknownBehavior('{:s}: TAxR {:04x} >= TAxCCR0 {:04x}'
                                               .format(repr(self), r, ccr0))
            elif MC == 2:
                if r >= 0xffff:
                    raise base.UnknownBehavior('{:s}: TAxR {:04x} >= ffff'
                                               .format(repr(self), r))
            self.TAxR = r
        return
