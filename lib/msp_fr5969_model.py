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
lower_size = 0xbb80 - 6 # Oh I get it.
# ROM has to have a long 0x00000000 at the end of it, which is 4 bytes,
# and .rodata is followed by .upper.data, which has at least the marker
# short 0x0001. So 6 bytes of ROM can't be filled by .rodata.
upper_start = 0x10000
upper_size = 0x3fff + 1 # I'm not sure why this offset of 1 doesn't break things.
resetvec = 0xfffe

reg_bitmask = (2 ** reg_bits) - 1
mem_bitmask = (2 ** mem_bits) - 1

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
        self.regs = [0 for _ in xrange(reg_size)]
        self.ram = [0 for _ in xrange(ram_size)]
        self.fram = [0 for _ in xrange(fram_size)]

        self.readreg = mk_readreg(self.regs) 
        self.writereg = mk_writereg(self.regs)
        self.read8 = mk_read8(self.ram, self.fram)
        self.write8 = mk_write8(self.ram, self.fram)
