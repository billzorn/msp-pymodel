# msp430 shared addressing logic

import utils
import msp_fr5969_model as model
import msp_instr as instr

# I think this ends up getting used to control all computed addresses;
# would be a good place to handle wrapping off the end of the address space
# behavior.
# Name is maybe a little confusing for that.
def mask_bw(a, bw):
    if bw == 0:
        return a & instr.pc_bitmask
    else:
        return a & model.reg_bitmask

# just a read selector; assumes but does not check that if bw is 0 then the 
# address must be even
def read_bw(state, a, bw):
    if bw == 0:
        return model.mk_read16(state.read8)(a)
    else:
        return state.read8(a)

# just a write selector; assumes but does not check that if bw is 0 then the
# address must be even
def write_bw(state, a, x, bw):
    if bw == 0:
        model.mk_write16(state.write8)(a, x)
    else:
        state.write8(a, x)

# addressing mode generators

def check_set_src(ins):
    return ins.smode == 'none' and ins.dmode == 'none'

def check_set_dst(ins):
    return ins.smode != 'none' and ins.dmode == 'none'

# given the right parameters, mutate instructions in place so that they do the
# right things to get their source and destination values

def setup_bits(ins, a_bitval, a_field, r_bitval, r_field, verbosity):
    (a_firstbit, a_lastbit) = ins.fields[a_field]
    if verbosity >= 3:
        print('assigning {:s} bits'.format(a_field))
        utils.explain_bitval(a_firstbit, a_lastbit, a_bitval)
    instr.set_bitval(ins.bits, a_firstbit, a_lastbit, a_bitval,
                     checkprev=True, preval=a_field)

    if not r_bitval is None:
        (r_firstbit, r_lastbit) = ins.fields[r_field]
        if verbosity >= 3:
            print('assigning {:s} bits'.format(r_field))
            utils.explain_bitval(r_firstbit, r_lastbit, r_bitval)
        instr.set_bitval(ins.bits, r_firstbit, r_lastbit, r_bitval,
                         checkprev=True, preval=r_field)
    
# mk_readfields: Instr -> (Model -> fields)
# readfields: Model -> fields
# keepreading: (Model, fields) -> Unit
# writefields: (Model, fields) -> Unit

def set_fmt1_src(ins, smode, n, mk_readfields, a_bitval,
                 a_field = 'as', r_bitval = None, r_field = 'rsrc', verbosity = 0):
    if verbosity >= 1:
        print('setting smode {:s}, {:s}'.format(ins.name, smode))
    assert(check_set_src(ins))
    
    setup_bits(ins, a_bitval, a_field, r_bitval, r_field, verbosity)

    ins.smode = smode
    ins.length += n
    ins.readfields = mk_readfields(ins)
    return

def set_fmt1_dst(ins, dmode, n, keepreading, writefields, a_bitval,
                 a_field = 'ad', r_bitval = None, r_field = 'rdst', verbosity = 0):
    if verbosity >= 1:
        print('setting dmode {:s}, {:s}'.format(ins.name, dmode))
    assert(check_set_dst(ins))

    setup_bits(ins, a_bitval, a_field, r_bitval, r_field, verbosity)
    
    # we need to store this rather than pulling it out of the object every time
    # otherwise there could be loopy issues
    readfields_src = ins.readfields

    def readfields_wrapper(state):
        fields = readfields_src(state)
        keepreading(state, fields)
        return fields

    ins.dmode = dmode
    ins.length += n
    ins.readfields = readfields_wrapper
    ins.writefields = writefields
    return

def set_fmt2_src(ins, smode, n, mk_readfields, writefields, a_bitval,
                 a_field = 'as', r_bitval = None, r_field = 'rsrc', verbosity = 0):
    if verbosity >= 1:
        print('setting smode {:s}, {:s}'.format(ins.name, smode))
    assert(check_set_src(ins))

    setup_bits(ins, a_bitval, a_field, r_bitval, r_field, verbosity)

    ins.smode = smode
    ins.length += n
    ins.readfields = mk_readfields(ins)
    ins.writefields = writefields
    return

# more convenience things for addressing modes

def mk_readfields_cg(ins, keepreading):
    def readfields(state):
        fields = instr.decode_cg(ins, state)
        if 'cgsrc' in fields:
            fields['src'] = fields['cgsrc']
            return fields
        else:
            keepreading(state, fields)
            return fields
    return readfields

def compute_and_read_addr(suffix, state, fields, offset = 0, offset_key = None):
    iname = 'i' + suffix
    aname = 'a' + suffix
    name = suffix
    instr.read_another_word(state, fields)
    fields[iname] = fields['words'][-1]
    # the idea is that we only read the fields AFTER we've invoked read_another_word
    if offset_key is None:
        k_offset = 0
    else:
        k_offset = fields[offset_key]
    fields[aname] = mask_bw(fields[iname] + offset + k_offset, fields['bw'])
    fields[name] = read_bw(state, fields[aname], fields['bw'])
    return
