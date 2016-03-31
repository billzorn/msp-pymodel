def explain_bitval(firstbit, lastbit, bitval, bits = 16):
    print('({:d}, {:d}) : {:d} [{:d}]'.format(firstbit, lastbit, bitval, bits))

    if 0 > firstbit or firstbit > lastbit or lastbit > (bits - 1):
        print('  nonsense bitrange {:d} - {:d}'.format(firstbit, lastbit))
        return

    field_bits = lastbit - firstbit + 1
    if field_bits <= 0:
        print('  nonsense field_bits {:d}'.format(field_bits))
        return

    max_bitval = (2 ** field_bits) - 1
    if bitval > max_bitval:
        print('  bitval does not fit in field: {:d} > 2 ** {:d} - 1 == {:d}'.format(bitval, field_bits, max_bitval))
        return

    print('  val {:x}'.format(bitval))
    
    l_bits = bits - 1 - lastbit
    r_bits = firstbit
    print(('  bin {:s}{:0' + str(field_bits) + 'b}{:s}').format('x'*l_bits, bitval, 'x'*r_bits))

    firstnybble = firstbit / 4
    lastnybble = lastbit / 4
    field_nybbles = lastnybble - firstnybble + 1
    nybbles = bits / 4
    adjusted_bitval = bitval << (firstbit - (firstnybble * 4))
    l_nybbles = nybbles - lastnybble - 1
    r_nybbles = firstnybble
    print(('  hex {:s}{:0' + str(field_nybbles) + 'x}{:s}').format('x'*l_nybbles, adjusted_bitval, 'x'*r_nybbles))
    return

class ExecuteError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class UnknownBehavior(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class RiskySuccess(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Ministate(object):
    def __init__(self, memvals, iswords = True, reg_size = 16):
        regs = [0 for _ in xrange(reg_size)]
        memlocs = len(memvals)
        if iswords:
            memlocs = memlocs * 2
        mem = [0 for _ in xrange(memlocs)]

        def readreg(r):
            return regs[r]

        def writereg(r, regval):
            regs[r] = regval
            return

        def read8(addr):
            if 0 <= addr and addr < len(mem):
                return mem[addr]
            return 0
        
        def write8(addr, byte):
            if 0 <= addr and addr <= len(mem):
                mem[addr] = byte
            return

        self.regs = regs
        self.mem = mem
        self.readreg = readreg
        self.writereg = writereg
        self.read8 = read8
        self.write8 = write8

        for i in xrange(len(memvals)):
            if iswords:
                self.write8(i * 2, memvals[i] & 0xff)
                self.write8((i * 2) + 1, (memvals[i] >> 8) & 0xff)
            else:
                self.write8(i, memvals[i] & 0xff)
