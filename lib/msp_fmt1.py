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
        raise base.UnknownBehavior('tried to keep reading after decoding cg for cg1 mode')
    return addr.mk_readfields_cg(ins, stopreading)

def mk_readfields_src_ind(ins):
    def keepreading(state, fields):
        fields['asrc'] = addr.mask_bw(state.readreg(fields['rsrc']), fields['bw'])
        fields['src'] = addr.read_bw(state, fields['asrc'], fields['bw'])
        return
    return addr.mk_readfields_cg(ins, keepreading)

def mk_readfields_src_ai(ins):
    def keepreading(state, fields):
        fields['asrc'] = state.readreg(fields['rsrc'])
        # you have to be careful to read from the masked address, but update the true one
        effective_addr = addr.mask_bw(fields['asrc'], fields['bw'])
        fields['src'] = addr.read_bw(state, effective_addr, fields['bw'])
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

def keepreading_dst_Rn(ins, state, fields):
    # Reading the PC is still weird.
    rn = fields['rdst']
    if rn == 0:
        fields['dst'] = instr.readpc(ins, fields)
    else:
        fields['dst'] = state.readreg(rn)
    return

def mk_writefields_dst_Rn(ins):
    def writefields_dst_Rn(state, fields):
        # special check for some PC-related behavior
        if fields['rdst'] == 0:
            if fields['bw'] == 1 and ins.name not in {'CMP', 'BIT'}:
                raise base.UnknownBehavior('fmt1 .B to PC')
            elif ins.name not in {'CMP', 'BIT', 'MOV'}:
                raise base.UnknownBehavior('fmt1 arithmetic not supported on PC (PUSH bug)')
            # we do permit BR
            # elif fields['dst'] != fields['pc']:
            #     raise base.UnknownBehavior('fmt1 indirect control flow: pc {:05x}, indirect to {:05x}'
            #                                .format(fields['pc'], fields['dst']))
        # and for writes to unmodeled SR bits
        elif fields['rdst'] == 2:
            if fields['dst'] & ((~271) & 0xfffff) != 0:
                raise base.UnknownBehavior('fmt1 invalid SR write: {:05x}'.format(fields['dst']))
        state.writereg(0, fields['pc'])
        state.writereg(fields['rdst'], fields['dst'])
        if not instr.is_sr_safe(ins):
            state.writereg(2, fields['sr'])
        return
    return writefields_dst_Rn

def keepreading_dst_idx(ins, state, fields):
    addr.compute_and_read_addr('dst', state, fields, offset=state.readreg(fields['rdst']))
    return

def mk_writefields_dst_idx(ins):
    def writefields_dst_idx(state, fields):
        if fields['rdst'] == 3:
            raise base.UnknownBehavior('fmt1 dst X(R3)')
        instr.write_pc_sr(state, fields)
        addr.write_bw(state, fields['adst'], fields['dst'], fields['bw'])
        return
    return writefields_dst_idx

def keepreading_dst_sym(ins, state, fields):
    # again, I think this will give the right offset
    addr.compute_and_read_addr('dst', state, fields, offset=-2, offset_key='pc')
    return

def mk_writefields_dst_sym(ins):
    def writefields_dst_sym(state, fields):
        instr.write_pc_sr(state, fields)
        addr.write_bw(state, fields['adst'], fields['dst'], fields['bw'])
        return
    return writefields_dst_sym

def keepreading_dst_abs(ins, state, fields):
    addr.compute_and_read_addr('dst', state, fields)
    return

# the logic is identical
mk_writefields_dst_abs = mk_writefields_dst_sym

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
    raise base.UnknownBehavior('execute dadd')
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
