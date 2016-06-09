from msp_isa import isa

# low level wrappers for isa methods

def _as(fmt, name, smode, dmode, fields):
    ins = isa.modes_to_instr(fmt, name, smode, dmode)
    #print('{:s} {:s} {:s} {:s}'.format(name, smode, dmode, repr(fields)))
    words = isa.inhabitant(ins, fields)
    return words

def assemble(name, smode, dmode, fields):
    fmt = isa.name_to_fmt[name]
    return _as(fmt, name, smode, dmode, fields)

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
    if mode in {'X(Rn)', 'ADDR', '&ADDR', '#@N', '#N'}:
        return True
    elif mode in {'Rn', '#1', '@Rn', '@Rn+', 'none'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def has_reg(mode):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return True
    elif mode in {'ADDR', '&ADDR', '#1', '#@N', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

# Will return None if the mode is not a cg mode. Otherwise will return
# the constant being generated, which might be 0 (which is False).
def has_cg(mode, rn):
    if mode == 'Rn':
        if rn == 3:
            return 0 # the same as reading the register
    elif mode == 'X(Rn)':
        if rn == 2:
            return 0 # alternative encoding of &ADDR mode
        elif rn == 3:
            return 1 # alternative encoding of #1 mode
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
    elif mode in {'Rn', '#1', '#@N', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def uses_reg(mode, rn):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return has_cg(mode, rn) is not None
    elif mode in {'ADDR', '&ADDR', '#1', '#@N', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

# assembly with dynamic computation of symbols
def assemble_sym(name, smode, dmode, symfields, pc):
    fields = {}
    for fieldname in symfields:
        sym_v = symfields[fieldname]
        if isinstance(sym_v, tuple):
            if sym_v[0] == 'PC_ABS':
                addr = sym_v[1]
                offs = pc
                if fieldname in {'isrc'}:
                    offs += 2
                elif fieldname in {'idst'}:
                    offs += 2
                    if has_immediate(smode):
                        offs += 2
                v = (addr - offs) & 0xffff # hard-coded 16-bit immediate
            else:
                raise ValueError('unsupported assembly directive: {:s}'.format(sym_v[0]))
        else:
            v = sym_v
        fields[fieldname] = v
    return assemble(name, smode, dmode, fields)

def assemble_symregion(instructions, base_pc):
    words = []
    pc = base_pc

    for args in instructions:
        new_words = assemble_sym(*(args + (pc,)))
        pc += len(new_words) * 2
        words += new_words

    return words

def region_size(instructions):
    size = 0
    for name, smode, dmode, fields in instructions:
        size += 2
        if has_immediate(smode):
            size += 2
        if has_immediate(dmode):
            size += 2

    return size
