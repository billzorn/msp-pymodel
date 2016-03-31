# msp430 instruction representation

import msp_base as base
import msp_fr5969_model as model

# Settings?
instr_bits = model.word_bits

# utilities
def field_to_bits(bitrange):
    (firstbit, lastbit) = bitrange
    return range(firstbit, lastbit + 1)

def set_bitval(bits, firstbit, lastbit, bitval, checkprev = False, preval = None):
    assert(0 <= firstbit and firstbit <= lastbit and lastbit < len(bits))
    assert(bitval < 2**(lastbit - firstbit + 1))
    for i in xrange(firstbit, lastbit + 1):
        if checkprev: 
            assert(bits[i] == preval)
        bits[i] = (bitval >> (i-firstbit)) & 1

def mk_checkbits(bits):
    def checkbits(word):
        assert word >= 0 and word < 2 ** len(bits)
        for i in xrange(len(bits)):
            if isinstance(bits[i], int):
                if not bits[i] == (word >> i) & 1:
                    return False
        return True
    return checkbits

# Things that control how operations on registers actually work
pc_bitmask = model.reg_bitmask & -2
def pcadd(pc, x):
    return (pc + x) & pc_bitmask

def pcidx(pc, old_pc):
    return (pc - old_pc) / 2

def regadd(r, x):
    return (r + x) & model.reg_bitmask

# Execution proceeds in three parts. First, readfields is called on a model
# to extract the necessary values based on the instruction's encoding. It
# presumably uses the model's readreg and read8 methods and produces a
# dictionary of field values keyed by name strings. In the case of autoincrementing
# register modes, readfields will generally perform the
# necessary state updates all by itself. In the case of the PC, readfields
# will store the fetched pc as old_pc, and then keep track of the expected PC
# as it autoincrements to read fields, anticipating a final PC write in writefields. 
# Execute takes the dict produced by readfields
# and does any computation specified by the instruction by mutating the values.
# Then, writefields writes the new values back to memory, taking the model
# and dict and presumably using the model's writereg and write8 methods.

# interface for reading and labeling words during decoding
def wordlabel(i):
    return 'word_' + str(i)
# read the next word after the pc, and increment the pc stored in fields
def read_another_word(state, fields):
    pc = fields['pc']
    idx = pcidx(pc, fields['old_pc'])
    word = mk_read16(state.read8)(pc)
    fields['pc'] = pcadd(pc, 2)
    fields[wordlabel(idx)] = word
    return idx
# get pc, sr, word_0, and autoincrement over this pc 
def decode_base(state):
    pc = state.readreg(0)
    sr = state.readreg(2)
    fields = {'old_pc':pc, 'pc':pc, 'sr':sr}
    idx = read_another_word(state, fields)
    if idx != 0:
        raise base.RiskySuccess(fields)
    else:
        return fields
# decode fields of a given instruction
def decode_fields(ins, state):
    fields = decode_base(state)
    word = fields[wordlabel(0)]
    for f in ins.fields:
        (firstbit, lastbit) = ins.fields[f]
        fields[f] = (word >> firstbit) & (2 ** (lastbit - firstbit + 1) - 1)
    return fields
# decode and then try to set up constant generator
def decode_cg(ins, state):
    fields = decode_fields(ins, state)
    if not ('as' in fields and 'rsrc' in fields):
        raise base.RiskySuccess(fields)
    f_as = fields['as']
    f_rsrc = fields['rsrc']
    if f_rsrc == 2:
        if f_as == 1:
            fields['cgsrc'] = 0
        elif f_as == 2:
            fields['cgsrc'] = 4
        elif f_as == 3:
            fields['cgsrc'] = 8
    elif f_rsrc == 3:
        if f_as == 0:
            fields['cgsrc'] = 0
        elif f_as == 1:
            fields['cgsrc'] = 1
        elif f_as == 2:
            fields['cgsrc'] = 2
        elif f_as == 3:
            if fields['bw'] == 1:
                fields['cgsrc'] = 0xff
            else:
                fields['cgsrc'] = 0xffff
    return fields

# basic actions performed after executing an instruction
def write_pc_sr(state, fields):
    state.writereg(0, fields['pc'])
    state.writereg(2, fields['sr'])

# default values used when instructions are first initialized: should be overwritten later
def readfields_default(state):
    return decode_base(state)

def execute_default(fields):
    # we don't want to do the pc update here, necessarily, as this would mean
    # we'd have to change the execute function based on the addressing mode
    raise base.ExecuteError('uninitialized exec')

def writefields_default(state, fields):
    write_pc_sr(state, fields)
    return

# Each instruction object contains the information necessary to decode and
# execute a single instruction, given an appropriate model. The idea is that
# specialized instruction instances can be created mechanically to handle the
# diversity of addressing modes.

class Instr(object):
    def __init__(self, opc, fields, 
                 name = 'NULL',
                 smode = 'none',
                 dmode = 'none',
                 fmt = 'none',
                 length = 2,
                 readfields = readfields_default,
                 execute = execute_default,
                 writefields = writefields_default,
                 verbosity = 0):

        if verbosity >= 3:
            print('created a new instruction {:s}'.format(name))

        self.name = name
        self.smode = smode
        self.dmode = dmode
        self.fmt = fmt
        self.length = length
        self.bits = [None for _ in xrange(instr_bits)]
        self.fields = fields

        for f in self.fields:
            (firstbit, lastbit) = self.fields[f]
            assert(0 <= firstbit and firstbit <= lastbit and lastbit < instr_bits)
            for i in xrange(firstbit, lastbit + 1):
                assert(self.bits[i] is None)
                self.bits[i] = f

        (opc_firstbit, opc_lastbit) = fields['opc']
        if verbosity >= 3:
            print('assigning opc bits')
            base.explain_bitval(opc_firstbit, opc_lastbit, opc)
        set_bitval(self.bits, opc_firstbit, opc_lastbit, opc, 
                   checkprev=True, preval='opc')

        self.checkbits = mk_checkbits(self.bits)
        self.readfields = readfields
        self.execute = execute
        self.writefields = writefields

    def describe(self):
        print('{:s} ({:s}) ({:s})'.format(self.name, self.smode, self.dmode))
        print('  format {:s}, length {:d}'.format(self.fmt, self.length))
        print('  ' + repr(self.bits))
        print('  ' + repr(self.fields))

    def tohex(self, fields = {}):
        # could add specially named extension fields for multiword encodings
        word = 0
        for i in xrange(len(self.bits)):
            if self.bits[i] == 1 or self.bits[i] == 0:
                word = word | self.bits[i] << i
            elif self.bits[i] in fields and self.bits[i] in self.fields:
                (firstbit, lastbit) = self.fields[self.bits[i]]
                assert(firstbit <= i and i <= lastbit)
                word = word | (fields[self.bits[i]] >> (i - firstbit)) & 1
        return '{:04x}'.format(word)