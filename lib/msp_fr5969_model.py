# fr5969 model parameters
reg_size = 16
reg_bits = 20
mem_bits = 8
word_bits = 2 * mem_bits

ram_size = 2048
ram_start = 0x1c00
fram_size = 64512
fram_start = 0x4400

ivec_start = 0xff90
ivec_count = 56
lower_start = fram_start
lower_size = 0xbb80
upper_start = 0x10000
upper_size = 0x4000
resetvec = 0xfffe

reg_bitmask = (2 ** reg_bits) - 1
mem_bitmask = (2 ** mem_bits) - 1

import msp_base as base
import utils

def iotrace_init():
    trace = []
    iotrace_next(trace)
    return trace

def iotrace_next(trace):
    trace.append({'r':{'reg':[], 'mem':[]},
                  'w':{'reg':[], 'mem':[]}})

def iotrace_append(trace, rw, regmem, addr, value):
    trace[-1][rw][regmem].append((addr, value))

def invoke_mmio(addr, v, handlers):
    if addr in handlers:
        return handlers[addr](v)
    else:
        raise base.ExecuteError('Unmapped address: {:05x}'.format(addr))

def mk_readreg(regs, trace = None):
    if trace is None:
        def readreg(r):
            return regs[r]
    else:
        def readreg(r):
            v = regs[r]
            iotrace_append(trace, 'r', 'reg', r, v)
            return v
    return readreg

def mk_writereg(regs, trace = None):
    if trace is None:
        def writereg(r, regval):
            assert isinstance(regval, int) and 0 <= regval and regval < 2**reg_bits
            if r != 3:
                regs[r] = regval
            return
    else:
        def writereg(r, regval):
            assert isinstance(regval, int) and 0 <= regval and regval < 2**reg_bits
            iotrace_append(trace, 'w', 'reg', r, regval)
            if r != 3:
                regs[r] = regval
            return
    return writereg

def mk_read8(ram, fram, handlers, trace = None):
    if trace is None:
        def read8(addr):
            if ram_start <= addr and addr < ram_start + ram_size:
                v = ram[addr - ram_start]
            elif fram_start <= addr and addr < fram_start + fram_size:
                v = fram[addr - fram_start]
            else:
                v = invoke_mmio(addr, None, handlers)
            #print('read {:05x} == {:02x}, notrace'.format(addr, v))
            return v
    else:
        def read8(addr):
            if ram_start <= addr and addr < ram_start + ram_size:
                v = ram[addr - ram_start]
            elif fram_start <= addr and addr < fram_start + fram_size:
                v = fram[addr - fram_start]
            else:
                v = invoke_mmio(addr, None, handlers)
            iotrace_append(trace, 'r', 'mem', addr, v)
            #print('read {:05x} == {:02x}, trace'.format(addr, v))
            return v
    return read8

def mk_write8(ram, fram, handlers, trace = None):
    if trace is None:
        def write8(addr, byte):
            #print('write {:05x} <- {:02x}, notrace'.format(addr, byte))
            assert isinstance(byte, int) and 0 <= byte and byte < 2**mem_bits
            if ram_start <= addr and addr < ram_start + ram_size:
                ram[addr - ram_start] = byte
            elif fram_start <= addr and addr < fram_start + fram_size:
                fram[addr - fram_start] = byte
            else:
                invoke_mmio(addr, byte, handlers)
                return
    else:
        def write8(addr, byte):
            #print('write {:05x} <- {:02x}, trace'.format(addr, byte))
            assert isinstance(byte, int) and 0 <= byte and byte < 2**mem_bits
            iotrace_append(trace, 'w', 'mem', addr, byte)
            if ram_start <= addr and addr < ram_start + ram_size:
                ram[addr - ram_start] = byte
            elif fram_start <= addr and addr < fram_start + fram_size:
                fram[addr - fram_start] = byte
            else:
                invoke_mmio(addr, byte, handlers)
                return
    return write8

def mk_read16(read8):
    # little endian
    def read16(addr):
        lo_bits = read8(addr)
        hi_bits = read8(addr+1)
        return lo_bits | (hi_bits << 8)
    return read16

def mk_write16(write8):
    # little endian
    def write16(addr, word):
        write8(addr, word & 0xff)
        write8(addr+1, (word >> 8) & 0xff)
        return
    return write16

class Model(object):
    def __init__(self, trace = None):
        self.regs = [0 for _ in range(reg_size)]
        self.ram = [(0xff if i % 2 == 0 else 0x3f) for i in range(ram_size)]
        self.fram = [0xff for _ in range(fram_size)]

        self.mmio_read = {}
        self.mmio_write = {}

        self.readreg = mk_readreg(self.regs, trace=trace) 
        self.writereg = mk_writereg(self.regs, trace=trace)
        self.read8 = mk_read8(self.ram, self.fram, self.mmio_read, trace=trace)
        self.write8 = mk_write8(self.ram, self.fram, self.mmio_write, trace=trace)

    def set_mmio_read_handler(self, addr, handler):
        assert (isinstance(addr, int) and not ((ram_start <= addr and addr < ram_start+ram_size)
                                               or (fram_start <= addr and addr < fram_start+fram_size)))
        self.mmio_read[addr] = handler

    def set_mmio_write_handler(self, addr, handler):
        assert (isinstance(addr, int) and not ((ram_start <= addr and addr < ram_start+ram_size)
                                               or (fram_start <= addr and addr < fram_start+fram_size)))
        self.mmio_write[addr] = handler

    def mmio_handle_default(self, addr, initial_value = 0):
        buf = [initial_value]
        def read_handler(v):
            return buf[0]
        def write_handler(v):
            buf[0] = v
            return
        self.set_mmio_read_handler(addr, read_handler)
        self.set_mmio_write_handler(addr, write_handler)

    def dump(self, check=True):
        print(repr(self))

        print('-- registers --')
        if check:
            regdump = utils.describe_regs(self.regs)
            assert(self.regs == utils.parse_regs(regdump))
        print(regdump)

        print('-- ram --')
        ramidump = utils.describe_interesting_memory(self.ram, ram_start, fill=[0xff, 0x3f])
        if check:
            ramdump = utils.describe_memory(self.ram, ram_start)
            assert(ramidump == utils.summarize_interesting(ramdump, fill=[0xff, 0x3f]))
            assert(self.ram == utils.parse_memory(ramdump))
        print(ramidump)

        print('-- fram --')
        framidump = utils.describe_interesting_memory(self.fram, fram_start, fill=[0xff])
        if check:
            framdump = utils.describe_memory(self.fram, fram_start)
            assert(framidump == utils.summarize_interesting(framdump, fill=[0xff]))
            assert(self.fram == utils.parse_memory(framdump))
        print(framidump)

    def segments(self):
        return (utils.interesting_regions(self.ram, ram_start, fill=[0xff, 0x3f], align=8) +
                utils.interesting_regions(self.fram, fram_start, fill=[0xff], align=8))

    def entry(self):
        return mk_read16(self.read8)(resetvec)

    def registers(self):
        return [self.readreg(i) for i in range(len(self.regs))]
