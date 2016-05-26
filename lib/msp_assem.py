from msp_isa import isa

# low level wrappers for isa methods

def _as(fmt, name, smode, dmode, fields):
    ins = isa.modes_to_instr(fmt, name, smode, dmode)
    words = isa.inhabitant(ins, fields)
    return words

def assemble(name, smode, dmode, fields):
    fmt = isa.name_to_fmt(name)
    return _as(fmt, name, smode, dmode)

# We record used registers as sets: this could be very compactly represented
# with machine integer backed bit sets, but whatever.
# We distinguish between two different ways to "use" a register: a "use" depends
# on the data in it, so other instructions are not free to overwrite it. A
# "clobber" puts unknown data into the register (due to expected differences
# between the hardware and the simulator) and needs to be cleaned up at some
# point.

class Reginfo(object):
    def __init__(self, uses = [], clobbers = []):
        self.uses = set(uses)
        self.clobbers = set(clobbers)

    def conflict(self, regs):
        for reg in regs:
            if reg in self.uses or reg in self.clobbers:
                return True
        return False

    def add(self, uses = [], clobbers = []):
        for use in uses:
            if use in self.uses or use in self.clobbers:
                raise ValueError('conflict: already using {:s}'.format(repr(use)))
            self.uses.add(use)
        for clobber in clobbers:
            self.clobbers.add(clobber)

# helpful predicates:

def has_immediate(mode):
    if mode in {'X(Rn)', 'ADDR', '&ADDR', '#N'}:
        return True
    elif mode in {'Rn', '#1', '@Rn', '@Rn+'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def has_reg(mode):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return True
    elif mode in {'ADDR', '&ADDR', '#1', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

# Will return None if the mode is not a cg mode. Otherwise will return
# the constant being generated, which might be 0 (which is False).
def has_cg(mode, rn):
    if mode == 'Rn':
        if rn == 3:
            return 0 # sort of...
    elif mode == 'X(Rn)':
        if rn == 2:
            return 0 # effectively
        elif rn == 3:
            return 1 # alternative encoding support
    elif mode == '@Rn':
        if rn == 2:
            return 4
        elif rn == 3:
            return 2
    elif mode == '@Rn+':
        if rn == 2:
            return 8
        elif rn == 3:
            return -1
    return None

def uses_addr(mode, rn):
    if mode in {'X(Rn)', 'ADDR', '&ADDR', '@Rn', '@Rn+'}:
        return not has_cg(mode, rn)
    elif mode in {'Rn', '#1', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def uses_reg(mode, rn):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return has_cg(mode, rn) is not None
    elif mode in {'ADDR', '&ADDR', '#1', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))


# would probably like to have good support for getting the right symbolic mode offset,
# not clear if that needs to be in here

# not entirely clear what to do with these
def mov_iaddr(i, addr):
    return assemble('MOV', '#N', '&ADDR', {'isrc':i, 'idst':addr, 'bw':0})

def mov_irn(i, rn):
    return assemble('MOV', '#N', 'Rn', {'isrc':i, 'rdst':rn, 'bw':0})

