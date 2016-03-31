# methods for defining jump instructions

import msp_instr as instr
import msp_arith as arith

# jump instructions share the same readfields and writefields, which communicate
# through the 'jump_offset' and 'jump_taken' fields

def mk_readfields(ins):
    def readfields(state):
        fields = instr.decode_fields(ins, state)
        fields['jump_offset'] = (fields['offset'] << 1) | (-fields['s'] << 10)
        return fields
    return readfields

def writefields(state, fields):
    pc = fields['pc']
    if fields['jump_taken']:
        pc = instr.pcadd(pc, fields['jump_offset'])
    state.writereg(0, pc)
    return

# the value of 'jump_taken', which controls whether or not the offset is added
# to the pc in writefields, is set by the execute logic

def execute_jnz(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['z'] == 0)
    return

def execute_jz(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['z'] == 1)
    return

def execute_jnc(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['c'] == 0)
    return

def execute_jc(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['c'] == 1)
    return

def execute_jn(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['n'] == 1)
    return

def execute_jge(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['n'] ^ sr_fields['v'] == 0)
    return

def execute_jl(fields):
    sr_fields = arith.unpack_sr(fields['sr'])
    fields['jump_taken'] = (sr_fields['n'] ^ sr_fields['v'] == 1)
    return

def execute_jmp(fields):
    fields['jump_taken'] = True
    return
