# methods for defining fmt1 instructions

import utils
import msp_base as base
import msp_instr as instr
import msp_addr as addr
import msp_arith as arith

# source modes

def mk_readfields_src_Rn(ins):
    def keepreading(state, fields):
        # Reading the PC is weird.
        # It might actually be cleaner to dynamically write the pc inside readfields? I don't know.
        rn = fields['rsrc']
        if rn == 0:
            fields['src'] = instr.readpc(ins, fields)
        else:
            fields['src'] = state.readreg(rn)
        return
    return addr.mk_readfields_cg(ins, keepreading)

def mk_readfields_src_idx(ins):
    def keepreading(state, fields):
        addr.compute_and_read_addr('src', state, fields, offset=state.readreg(fields['rsrc']))
        return
    return addr.mk_readfields_cg(ins, keepreading)

def mk_readfields_src_sym(ins):
    def readfields(state):
        fields = instr.decode_fields(ins, state)
        # I think the value of the pc will be "correct" here, as determined
        # by consistent use of read_another_word
        # JK!!! There was an off by 1 (well, one word, so use offset of -2)
        addr.compute_and_read_addr('src', state, fields, offset=-2, offset_key='pc')
        return fields
    return readfields

def mk_readfields_src_abs(ins):
    def readfields(state):
        fields = instr.decode_fields(ins, state)
        addr.compute_and_read_addr('src', state, fields)
        return fields
    return readfields

def mk_readfields_src_cg1(ins):
    def stopreading(state, fields):
        raise base.RiskySuccess(fields)
    return addr.mk_readfields_cg(ins, stopreading)

def mk_readfields_src_ind(ins):
    def keepreading(state, fields):
        fields['asrc'] = addr.mask_bw(state.readreg(fields['rsrc']), fields['bw'])
        fields['src'] = addr.read_bw(state, fields['asrc'], fields['bw'])
        return
    return addr.mk_readfields_cg(ins, keepreading)

def mk_readfields_src_ai(ins):
    def keepreading(state, fields):
        fields['asrc'] = addr.mask_bw(state.readreg(fields['rsrc']), fields['bw'])
        fields['src'] = addr.read_bw(state, fields['asrc'], fields['bw'])
        # mutate the incremented register in place
        # for some reason, the SP is incremented by two even in byte mode...
        # also wrapping?
        if fields['bw'] == 0 or fields['rsrc'] == 1:
            offset = 2
        else:
            offset = 1
        state.writereg(fields['rsrc'], instr.regadd(fields['asrc'], offset))
        return
    return addr.mk_readfields_cg(ins, keepreading)

def mk_readfields_src_N(ins):
    def readfields(state):
        fields = instr.decode_fields(ins, state)
        instr.read_another_word(state, fields)
        fields['isrc'] = fields['words'][-1]
        fields['src'] = fields['isrc']
        return fields
    return readfields

# destination modes

def keepreading_dst_Rn(state, fields):
    fields['dst'] = state.readreg(fields['rdst'])
    return

def writefields_dst_Rn(state, fields):
    instr.write_pc_sr(state, fields)
    state.writereg(fields['rdst'], fields['dst'])
    return

def keepreading_dst_idx(state, fields):
    addr.compute_and_read_addr('dst', state, fields, offset=state.readreg(fields['rdst']))
    return

def writefields_dst_idx(state, fields):
    if fields['rdst'] == 3:
        raise base.UnknownBehavior('fmt1 dst X(R3)')
    instr.write_pc_sr(state, fields)
    addr.write_bw(state, fields['adst'], fields['dst'], fields['bw'])
    return

def keepreading_dst_sym(state, fields):
    # again, I think this will give the right offset
    addr.compute_and_read_addr('dst', state, fields, offset=-2, offset_key='pc')
    return

def writefields_dst_sym(state, fields):
    instr.write_pc_sr(state, fields)
    addr.write_bw(state, fields['adst'], fields['dst'], fields['bw'])
    return

def keepreading_dst_abs(state, fields):
    addr.compute_and_read_addr('dst', state, fields)
    return

# the logic is identical
writefields_dst_abs = writefields_dst_sym

# exec logic

def execute_mov(fields):
    bits = arith.howmanybits(fields)
    result = fields['src']
    fields['dst'] = arith.trunc_bits(result, bits)
    return

def execute_add(fields):
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: dst + src,
                        arith.vbit_add)
    return

def execute_addc(fields):
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: dst + src + sr_fields['c'],
                        arith.vbit_add)
    return


def execute_sub(fields):
    bits = arith.howmanybits(fields)
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: arith.trunc_bits(~src, bits) + 1 + dst,
                        arith.vbit_sub)
    return

def execute_subc(fields):
    bits = arith.howmanybits(fields)
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: arith.trunc_bits(~src, bits) + sr_fields['c'] + dst,
                        arith.vbit_sub)
    return

def execute_cmp(fields):
    bits = arith.howmanybits(fields)
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: arith.trunc_bits(~src, bits) + 1 + dst,
                        arith.vbit_sub,
                        write_dst=False)
    return

def execute_dadd(fields):
    # requires BCD math
    if fields['bw'] == 1:
        local_bcd_add = arith.mk_bcd_add(8)
    else:
        local_bcd_add = arith.mk_bcd_add(16)
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: local_bcd_add(src, dst),
                        arith.vbit_add) # accodring to the manual, vbit is undefined, this is almost certainly wrong
    return

def execute_bit(fields):
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: dst & src,
                        None,
                        write_dst=False, alt_cbit=True, clr_vbit=True)
    return

def execute_bic(fields):
    bits = arith.howmanybits(fields)
    result = (~fields['src']) & fields['dst']
    fields['dst'] = arith.trunc_bits(result, bits)
    return

def execute_bis(fields):
    bits = arith.howmanybits(fields)
    result = fields['src'] | fields['dst']
    fields['dst'] = arith.trunc_bits(result, bits)
    return

def execute_xor(fields):
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: dst ^ src,
                        arith.vbit_xor,
                        alt_cbit=True)
    return

def execute_and(fields):
    arith.execute_arith(fields,
                        lambda src, dst, sr_fields: dst & src,
                        None,
                        alt_cbit=True, clr_vbit=True)
    return
