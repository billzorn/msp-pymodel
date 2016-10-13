# methods for defining fmt1 instructions

import msp_base as base
import msp_fr5969_model as model
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

# ...except for the strange behavior where PUSH and CALL see r1-2
# in idx mode, as if they'd already decremented the register
# when they read from it. Yes, only in idx mode. the other modes
# see the pre-decrement value of r1 as expected.

def mk_readfields_src_idx_push_call(ins):
    def keepreading(state, fields):
        rsrc = fields['rsrc']
        offset = state.readreg(rsrc)
        if rsrc == 1:
            offset = instr.regadd(offset, -2)
        addr.compute_and_read_addr('src', state, fields, offset=offset)
        return
    return addr.mk_readfields_cg(ins, keepreading)

# ...and for the strange behavior where @SP+ autoincrement is ignored
# by instructions that update the stack pointer automatically (PUSH, CALL).

def mk_readfields_src_ai_push_call(ins):
    def keepreading(state, fields):
        fields['asrc'] = state.readreg(fields['rsrc'])
        # you have to be careful to read from the masked address, but update the true one
        effective_addr = addr.mask_bw(fields['asrc'], fields['bw'])
        fields['src'] = addr.read_bw(state, effective_addr, fields['bw'])
        # mutate the incremented register in place.
        # PUSH and CALL just drop the sp write you'd expect from ai mode, and do their
        # normal stack pointer manipulation as if @SP mode had been used instead of @SP+.
        if fields['rsrc'] != 1:
            if fields['bw'] == 0:
                offset = 2
            else:
                offset = 1
            state.writereg(fields['rsrc'], instr.regadd(fields['asrc'], offset))
        return
    return addr.mk_readfields_cg(ins, keepreading)

# destination modes, which are kind of like the source modes

def mk_writefields_src_Rn(ins):
    def writefields_src_Rn(state, fields):
        if fields['rsrc'] in {0,2}:
            raise base.UnknownBehavior('fmt2 write to R{:d} unsupported'
                                       .format(fields['rsrc']))
        state.writereg(0, fields['pc'])
        state.writereg(fields['rsrc'], fields['src'])
        if not instr.is_sr_safe(ins):
            state.writereg(2, fields['sr'])
        return
    return writefields_src_Rn

def mk_writefields_src_idx(ins):
    def writefields_src_idx(state, fields):
        if 'cgsrc' in fields:
            raise base.UnknownBehavior('cg unsupported for fmt2')
        instr.write_pc_sr(state, fields)
        # I don't think the funny business with X(R3) can occur here because this isn't
        # really a destination mode
        addr.write_bw(state, fields['asrc'], fields['src'], fields['bw'])
        return
    return writefields_src_idx

# identical logic
mk_writefields_src_sym = mk_writefields_src_idx
mk_writefields_src_abs = mk_writefields_src_idx
mk_writefields_src_ind = mk_writefields_src_idx
mk_writefields_src_ai  = mk_writefields_src_idx

def mk_writefields_src_N(ins):
    def writefields_src_N(state, fields):
        raise base.UnknownBehavior('fmt2 dst #N')
    return writefields_src_N

def mk_writefields_src_cg1(ins):
    def writefields_src_cg1(state, fields):
        raise base.UnknownBehavior('fmt2 dst cg1')
    return writefields_src_cg1

# execution logic

def execute_rrc(fields):
    bits = arith.howmanybits(fields)
    arith.execute_shift(fields,
                        lambda src, sr_fields: ((src >> 1) & (~(1 << (bits-1)))) | (sr_fields['c'] << (bits-1)))
    return

def execute_swpb(fields):
    if fields['bw'] != 0:
        raise base.UnknownBehavior('swpb bw={:d}'.format(fields['bw']))
    bits = 16
    src = arith.trunc_bits(fields['src'], bits)
    result_t = ((src & 0xff) << 8) | ((src >> 8) & 0xff)
    fields['src'] = result_t
    return

def execute_rra(fields):
    bits = arith.howmanybits(fields)
    arith.execute_shift(fields,
                        lambda src, sr_fields: ((src >> 1) & (~(1 << (bits-1)))) | (src & (1 << (bits-1))))
    return

def execute_sxt(fields):
    if fields['bw'] != 0:
        raise base.UnknownBehavior('sxt bw={:d}'.format(fields['bw']))
    bits = 8
    extbits = 16
    sr_fields = arith.unpack_sr(fields['sr'])
    result_t = arith.sxt_bits(fields['src'], bits, extbits)
    sr_fields['n'] = arith.nbit(result_t, extbits)
    sr_fields['z'] = arith.zbit(result_t)
    sr_fields['c'] = 1 ^ sr_fields['z']
    sr_fields['v'] = 0
    fields['src'] = result_t
    fields['sr'] = arith.pack_sr(sr_fields)
    return

# special execution logic, which goes in writefields

def execute_push(fields):
    return
def mk_writefields_push(ins):
    def writefields_push(state, fields):
        if ins.smode not in {'Rn'} and fields['rsrc'] in {1}:
            raise base.UnknownBehavior('PUSH indirect through SP unsupported')
        instr.write_pc_sr(state, fields)
        # I think this sp manipulation does the right thing
        sp = instr.regadd(state.readreg(1), -2)
        state.writereg(1, sp)
        # We have to truncate the source to 8 bits somewhere... might be better to
        # eventually change this to happen in readfields.
        bits = arith.howmanybits(fields)
        src = arith.trunc_bits(fields['src'], bits)
        addr.write_bw(state, sp, src, fields['bw'])
        return
    return writefields_push

def execute_call(fields):
    return

def mk_writefields_call(ins):
    def writefields_call(state, fields):
        if ins.smode in {'Rn'} and fields['rsrc'] in {0,1,2,3}:
            raise base.UnknownBehavior('unsupported: CALL R{:d}'.format(fields['rsrc']))
        elif 'cgsrc' in fields:
            raise base.UnknownBehavior('CALL to CG value unsupported')
        elif fields['rsrc'] in {1}:
            raise base.UnknownBehavior('CALL indirect through SP unsupported')
        # I don't know what happens if, for example, the sp isn't word aligned...
        sp = instr.regadd(state.readreg(1), -2)
        state.writereg(1, sp)
        # What about the high bits of the pc ????
        model.mk_write16(state.write8)(sp, fields['pc'])
        state.writereg(0, fields['src'])
        return
    return writefields_call

def execute_reti(fields):
    if fields['bw'] == 1:
        raise base.UnknownBehavior('RETI.B == CALLA')
    return

def mk_writefields_reti(ins):
    def writefields_reti(state, fields):
        if not (ins.smode in {'Rn'} and fields['rsrc'] == 0):
            raise base.UnknownBehavior('RETI only supported with Rn R0 mode')
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
    return writefields_reti
