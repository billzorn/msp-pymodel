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

# should remove, not a good idea
class RiskySuccess(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Breakpoint(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Ministate(object):
    def __init__(self, memvals, iswords = True, reg_size = 16):
        regs = [0 for _ in range(reg_size)]
        memlocs = len(memvals)
        if iswords:
            memlocs = memlocs * 2
        mem = [0 for _ in range(memlocs)]

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

        for i in range(len(memvals)):
            if iswords:
                self.write8(i * 2, memvals[i] & 0xff)
                self.write8((i * 2) + 1, (memvals[i] >> 8) & 0xff)
            else:
                self.write8(i, memvals[i] & 0xff)
