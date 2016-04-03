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

import re
import utils

def mspdump_describe_regs(regs):
    regstr = '( PC: {:05x}) ( R4: {:05x}) ( R8: {:05x}) (R12: {:05x})\n'.format(
        regs[0], regs[4], regs[8], regs[12])
    regstr += '( SP: {:05x}) ( R5: {:05x}) ( R9: {:05x}) (R13: {:05x})\n'.format(
        regs[1], regs[5], regs[9], regs[13])
    regstr += '( SR: {:05x}) ( R6: {:05x}) (R10: {:05x}) (R14: {:05x})\n'.format(
        regs[2], regs[6], regs[10], regs[14])
    regstr += '( R3: {:05x}) ( R7: {:05x}) (R11: {:05x}) (R15: {:05x})'.format(
        regs[3], regs[7], regs[11], regs[15])
    return regstr

def mspdump_describe_memory_row(mem, addr, idx, cols = 16):
    used_cols = min(cols, len(mem) - idx)
    unused_cols = cols - used_cols
    bin_fmt = '{:05x}:' + (' {:02x}' * used_cols) + ('   ' * unused_cols)
    str_fmt = ('{:s}' * used_cols) + (' ' * unused_cols)
    row_values = mem[idx:idx+used_cols]

    return (bin_fmt.format(addr + idx, *row_values) + ' |' +
            re.sub(utils.unprintable_re, '.', str_fmt.format(*map(chr, row_values))) + '|')

def mspdump_describe_memory(mem, addr, cols = 16):
    memstr = ''
    for idx in range(0, len(mem), cols):
        memstr += mspdump_describe_memory_row(mem, addr, idx, cols = cols)
        if idx < len(mem) - cols:
            memstr += '\n'
    return memstr

def mspdump_describe_interesting_memory(mem, addr, fill = [0xff], cols=16):
    memstr = ''
    boring_row = fill * (cols // len(fill))
    if len(boring_row) < cols:
        boring_row += fill
    if len(boring_row) > cols:
        boring_row = boring_row[:cols]
    fill_description = '[' + (' {:02x}' * len(fill)).format(*fill) + ' ]'
           
    boring_count = 0
    for idx in range(0, len(mem), cols):
        used_cols = min(cols, len(mem) - idx)
        unused_cols = cols - used_cols
        row_values = mem[idx:idx+used_cols]
        if row_values == boring_row:
            boring_count += 1
        else:
            if boring_count > 0:
                memstr += '{:s} for {:d} bytes ({:d} rows)\n'.format(fill_description, boring_count * cols, boring_count)
                boring_count = 0
            memstr += mspdump_describe_memory_row(mem, addr, idx, cols = cols)
            if idx < len(mem) - cols:
                memstr += '\n'
    if boring_count > 0:
        memstr += '{:s} for {:d} bytes ({:d} rows)'.format(fill_description, boring_count * cols, boring_count)
    return memstr

def mk_readreg(regs):
    def readreg(r):
        return regs[r]
    return readreg

def mk_writereg(regs):
    def writereg(r, regval):
        if r != 3:
            regs[r] = regval
        return
    return writereg

def mk_read8(ram, fram):
    def read8(addr):
        if ram_start <= addr and addr < ram_start + ram_size:
            return ram[addr - ram_start]
        elif fram_start <= addr and addr < fram_start + fram_size:
            return fram[addr - fram_start]
        else:
            # what's the right thing to do here?????
            return 0
    return read8

def mk_write8(ram, fram):
    def write8(addr, byte):
        ####print('writing {:#02x} to address {:#04x}'.format(byte, addr))
        if ram_start <= addr and addr < ram_start + ram_size:
            ram[addr - ram_start] = byte
        elif fram_start <= addr and addr < fram_start + fram_size:
            fram[addr - fram_start] = byte
        else:
            # what's the right thing to do here????
            print('writing {:#02x} to address {:#04x}'.format(byte, addr))
            return
    return write8

def mk_read16(read8):
    # little endian
    def read16(addr):
        # what's read8's failure behavior if we try to go off the end of memory?
        return read8(addr) | (read8(addr+1) << 8)
    return read16

def mk_write16(write8):
    # little endian
    def write16(addr, word):
        # what's write8's failure behavior?
        write8(addr, word & 0xff)
        write8(addr+1, (word >> 8) & 0xff)
        return
    return write16

class Model(object):
    def __init__(self):
        self.regs = [0 for _ in range(reg_size)]
        self.ram = [(0xff if i % 2 == 0 else 0x3f) for i in range(ram_size)]
        self.fram = [0xff for _ in range(fram_size)]

        self.readreg = mk_readreg(self.regs) 
        self.writereg = mk_writereg(self.regs)
        self.read8 = mk_read8(self.ram, self.fram)
        self.write8 = mk_write8(self.ram, self.fram)

    def dump(self):
        print(repr(self))
        print('-- registers --')
        print(mspdump_describe_regs(self.regs))
        print('-- ram --')
        print(mspdump_describe_interesting_memory(self.ram, ram_start, fill = [0xff, 0x3f]))
        print('-- fram --')
        print(mspdump_describe_interesting_memory(self.fram, fram_start, fill = [0xff]))
        print('')
