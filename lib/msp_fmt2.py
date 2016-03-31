# methods for defining fmt1 instructions

import msp_base as base
import msp_instr as instr
import msp_addr as addr
import msp_arith as arith

# for source modes, we can reuse the mk_readfields code from fmt1

import msp_fmt1 as fmt1
mk_readfields_src_Rn  = fmt1.mk_readfields_src_Rn
mk_readfields_src_idx = fmt1.mk_readfields_src_idx
mk_readfields_src_sym = fmt1.mk_readfields_src_sym
mk_readfields_src_abs = fmt1.mk_readfields_src_abs
mk_readfields_src_ind = fmt1.mk_readfields_src_ind
mk_readfields_src_ai  = fmt1.mk_readfields_src_ai
mk_readfields_src_N   = fmt1.mk_readfields_src_N
mk_readfields_src_cg1 = fmt1.mk_readfields_src_cg1

# destination modes, which are kind of like the source modes

def writefields_src_Rn(state, fields):
    instr.write_pc_sr(state, fields)
    state.writereg(fields['rsrc'], fields['src'])
    return

def writefields_src_idx(state, fields):
    instr.write_pc_sr(state, fields)
    # I don't think the funny business with X(R3) can occur here because this isn't
    # really a destination mode
    addr.write_bw(state, fields['asrc'], fields['src'], fields['bw'])
    return

# identical logic
writefields_src_sym = writefields_src_idx
writefields_src_abs = writefields_src_idx
writefields_src_ind = writefields_src_idx
writefields_src_ai  = writefields_src_idx

def writefields_src_N(state, fields):
    raise base.UnknownBehavior('fmt2 dst #N')

def writefields_src_cg1(state, fields):
    raise base.UnknownBehavior('fmt2 dst cg1')

# execution logic

def execute_rrc(fields):
    bits = arith.howmanybits(fields)
    arith.execute_shift(fields,
                        lambda src, sr_fields: ((src >> 1) & (~(1 << (bits-1)))) | sr_fields['c'])
    return

def execute_swpb(fields):
    if fields['bw'] != 0:
        raise base.UnknownBehavior('swpb bw={:d}'.format(fields['bw']))
    bits = 16
    src = trunc_bits(fields['src'], bits)
    result_t = (src << 8) | (src & 255)
    fields['src'] = result_t
    return

def execute_rra(fields):
    bits = arith.howmanybits(fields)
    arith.execute_shift(fields,
                        lambda src, sr_fields: ((src >> 1) & (~(1 << (bits-1)))) | (src & (1 << (bits-1))))
    return

def execute_sxt(fields):
    if fields['bw'] != 0:
        raise base.UnknownBehavior('swpb bw={:d}'.format(fields['bw']))
    bits = 8
    extbits = 16
    result_t = arith.sxt_bits(fields['src'], bits, extbits)
    sr_fields['n'] = nbit(result_t, extbits)
    sr_fields['z'] = zbit(result_t)
    sr_fields['c'] = 1 ^ sr_fields['z']
    sr_fields['v'] = 0
    fields['src'] = result_t
    fields['sr'] = pack_sr(sr_fields)
    return

# special execution logic, which goes in writefields

def execute_push(fields):
    return

def writefields_push(state, fields):
    instr.write_pc_sr(state, fields)
    # I think this sp manipulation does the right thing
    sp = instr.regadd(state.readreg(1), -2)
    addr.write_bw(state, sp, fields['src'], fields['bw'])
    return

def execute_call(fields):
    return

def writefields_call(state, fields):
    # I don't know what happens if, for example, the sp isn't word aligned...
    sp = instr.regadd(state.readreg(1), -2)
    # What about the high bits of the pc ????
    model.mk_write16(state.write8)(sp, fields['pc'])
    state.writereg(0, fields['src'])
    return

def execute_reti(fields):
    return

def writefields_reti(state, fields):
    read16 = model.mk_read16(state.read8)
    sp = state.readreg(1)
    sr = read16(sp)
    sp = instr.regadd(sp, 2)
    pc = read16(sp)
    sp = instr.regadd(sp, 2)
    # some of pc is recovered from SR, but it's not really clear where
    pc = pc | ((sr & 0xf000) << 16)
    state.writereg(0, pc)
    state.writereg(1, sp)
    state.writereg(2, sr)
    return
