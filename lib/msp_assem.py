import msp_fr5969_model as model
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
    def __init__(self, uses = {}, clobbers = []):
        self.uses = uses
        self.clobbers = set(clobbers)

    def conflict(self, reg):
        if reg in self.uses:
            return self.uses[reg]
        elif reg in self.clobbers:
            return True
        return False

    def add(self, uses = {}, clobbers = []):
        for use in uses:
            if use in self.uses:
                raise ValueError('conflict: already using {:s}'.format(repr(use)))
            self.uses[use] = uses[use]
        for clobber in clobbers:
            self.clobbers.add(clobber)

    # returns the value if already set, and the check passes. if the check fails, raises
    # an exception. returns false (and does't check!) if not already set.
    def check_or_set_use(self, rn, pred, default):
        if rn in self.uses:
            if not pred(self.uses[rn]):
                raise ValueError('conflict: predicate {:s} failed for {:x}: {:s}'
                                 .format(repr(pred), rn, repr(self.uses[rn])))
            return self.uses[rn]
        else:
            self.uses[rn] = default
            return False

    def overwrite_or_set_use(self, rn, x):
        if rn in self.uses:
            self.uses[rn] = x
            # we did overwrite
            return True
        else:
            self.uses[rn] = x
            # set the value anyway
            return False

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
    elif mode in {'ADDR', '&ADDR', '#1', '#@N', '#N', 'none'}:
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
    elif mode in {'Rn', '#1', '#@N', '#N', 'none'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def uses_reg(mode, rn):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return has_cg(mode, rn) is not None
    elif mode in {'ADDR', '&ADDR', '#1', '#@N', '#N', 'none'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def modifies_destination(name):
    if name in {'MOV', 'ADD', 'ADDC', 'SUBC', 'SUB', 'DADD', 'BIC', 'BIS', 'XOR', 'AND',
                'RRC', 'SWPB', 'RRA', 'SXT'}:
        return True
    else:
        return False

def modifies_sr(name):
    if name in {'ADD', 'ADDC', 'SUBC', 'SUB', 'CMP', 'DADD', 'BIT', 'XOR', 'AND',
                'RRC', 'RRA', 'RETI', 'SXT'}:
        return True
    else:
        return False

# assembly with dynamic computation of symbols
def assemble_sym(name, smode, dmode, symfields, pc, labels):
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
                v = (addr - offs) & 0xffff #TODO hard-coded 16-bit immediate
            elif sym_v[0] == 'LABEL':
                # initial implementation: immediate lookup
                v = labels[sym_v[1]]
                # This requires all of the addresses to be precomputed if we want to
                # be able to jump to labels after this instruction.
            elif sym_v[0] == 'JLABEL':
                # offset to jump label
                addr = labels[sym_v[1]]
                offs = pc + 2
                immediate = (addr - offs) & 0x7ff #TODO hard-coded 11-bit immediate
                v = immediate >> 1 & 0x3ff #TODO hard-coded 9-bit immediate
            elif sym_v[0] == 'JSIGN':
                # sign for offset to jump label
                addr = labels[sym_v[1]]
                offs = pc + 2
                immediate = (addr - offs) & 0x7ff #TODO hard-coded 11-bit immediate
                v = immediate >> 10 & 0x1
            else:
                raise ValueError('unsupported assembly directive: {:s}'.format(sym_v[0]))
        else:
            v = sym_v
        fields[fieldname] = v
    return assemble(name, smode, dmode, fields)

def assemble_symregion(instructions, base_pc, labels = {}):
    # precompute addresses of labels
    pc_pre = base_pc
    for args in instructions:
        if isinstance(args, str):
            labels[args] = pc_pre
        else:
            name, smode, dmode, fields = args
            pc_pre += 2
            if has_immediate(smode):
                pc_pre += 2
            if has_immediate(dmode):
                pc_pre += 2
            
    # go back and generate encoding
    words = []
    pc = base_pc
    for args in instructions:
        if isinstance(args, str):
            assert labels[args] == pc
        else:
            new_words = assemble_sym(*(args + (pc, labels)))
            pc += len(new_words) * 2
            words += new_words

    # for label in labels:
    #     print('{:s} : {:s}'.format(label, hex(labels[label])))

    assert pc == pc_pre
    return words

def region_size(instructions):
    size = 0
    for args in instructions:
        if isinstance(args, str):
            # label, skip
            continue
        else:
            name, smode, dmode, fields = args
            size += 2
            if has_immediate(smode):
                size += 2
            if has_immediate(dmode):
                size += 2

    return size
