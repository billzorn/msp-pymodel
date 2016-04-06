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

import utils

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
        print(utils.describe_regs(self.regs))

        print('-- ram --')
        ramidump = utils.describe_interesting_memory(self.ram, ram_start, fill=[0xff, 0x3f])
        ramdump = utils.describe_memory(self.ram, ram_start)
        assert(ramidump == utils.summarize_interesting(ramdump, fill=[0xff, 0x3f]))
        print(ramidump)

        print('-- fram --')
        framidump = utils.describe_interesting_memory(self.fram, fram_start, fill=[0xff])
        framdump = utils.describe_memory(self.fram, fram_start)
        assert(framidump == utils.summarize_interesting(framdump, fill=[0xff]))
        print(framidump)

        print('')

    def segments(self):
        return (utils.interesting_regions(self.ram, ram_start, fill=[0xff, 0x3f], align=8) +
                utils.interesting_regions(self.fram, fram_start, fill=[0xff], align=8))

    def entry(self):
        return mk_read16(self.read8)(resetvec)

    def registers(self):
        return [self.readreg(i) for i in range(len(self.regs))]
