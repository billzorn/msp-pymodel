# msp430 instruction table

import utils
import msp_instr as instr
import msp_addr as addr
import msp_fmt1
import msp_fmt2
import msp_jump

fmt1 = {
    'fields' : {
        'rdst' : (0,  3, ),
        'as'   : (4,  5, ),
        'bw'   : (6,  6, ),
        'ad'   : (7,  7, ),
        'rsrc' : (8,  11,),
        'opc'  : (12, 15,),
    },
    'instructions' : {
    #    name     opc  execute
        'MOV'  : (0x4, msp_fmt1.execute_mov, ),
        'ADD'  : (0x5, msp_fmt1.execute_add, ),
        'ADDC' : (0x6, msp_fmt1.execute_addc,),
        'SUBC' : (0x7, msp_fmt1.execute_subc,),
        'SUB'  : (0x8, msp_fmt1.execute_sub, ),
        'CMP'  : (0x9, msp_fmt1.execute_cmp, ),
        'DADD' : (0xA, msp_fmt1.execute_dadd,),
        'BIT'  : (0xB, msp_fmt1.execute_bit, ),
        'BIC'  : (0xC, msp_fmt1.execute_bic, ),
        'BIS'  : (0xD, msp_fmt1.execute_bis, ),
        'XOR'  : (0xE, msp_fmt1.execute_xor, ),
        'AND'  : (0xF, msp_fmt1.execute_and, ),
    },
    'smodes' : {
    #    smode     n  mk_readfieds                    a_bitval r_bitval
        'Rn'    : (0, msp_fmt1.mk_readfields_src_Rn,  0,       None,),
        'X(Rn)' : (2, msp_fmt1.mk_readfields_src_idx, 1,       None,),
        'ADDR'  : (2, msp_fmt1.mk_readfields_src_sym, 1,       0,   ),
        '&ADDR' : (2, msp_fmt1.mk_readfields_src_abs, 1,       2,   ),
        '#1'    : (0, msp_fmt1.mk_readfields_src_cg1, 1,       3,   ),
        '@Rn'   : (0, msp_fmt1.mk_readfields_src_ind, 2,       None,),
        '@Rn+'  : (0, msp_fmt1.mk_readfields_src_ai,  3,       None,),
        '#N'    : (2, msp_fmt1.mk_readfields_src_N,   3,       0,   ),
    },
    'dmodes' : {
    #    dmode     n  keepreading                   writefields                   a_bitval r_bitval
        'Rn'    : (0, msp_fmt1.keepreading_dst_Rn,  msp_fmt1.writefields_dst_Rn,  0,       None,),
        'X(Rn)' : (2, msp_fmt1.keepreading_dst_idx, msp_fmt1.writefields_dst_idx, 1,       None,),
        'ADDR'  : (2, msp_fmt1.keepreading_dst_sym, msp_fmt1.writefields_dst_sym, 1,       0,   ),
        '&ADDR' : (2, msp_fmt1.keepreading_dst_abs, msp_fmt1.writefields_dst_abs, 1,       2,   ),
    },
}

def create_fmt1(name, smode, dmode, verbosity = 0):
    opc, execute = fmt1['instructions'][name]
    ins = instr.Instr(opc, fmt1['fields'], name=name, fmt='fmt1', verbosity=verbosity)

    n, mk_readfields, a_bitval, r_bitval = fmt1['smodes'][smode]
    addr.set_fmt1_src(ins, smode, n, mk_readfields, a_bitval,
                      r_bitval=r_bitval, verbosity=verbosity)

    n, keepreading, writefields, a_bitval, r_bitval = fmt1['dmodes'][dmode]
    addr.set_fmt1_dst(ins, dmode, n, keepreading, writefields, a_bitval,
                      r_bitval=r_bitval, verbosity=verbosity)

    ins.execute = execute
    return ins

fmt2 = {
    'fields' : {
        'rsrc' : (0, 3, ),
        'as'   : (4, 5, ),
        'bw'   : (6, 6, ),
        'opc'  : (7, 15,),
    },
    'instructions' : {
    #    name     opc   execute                writefields_exec               instruction map
        'RRC'  : (0x20, msp_fmt2.execute_rrc,  None,                     ), # 10xx | 000
        'SWPB' : (0x21, msp_fmt2.execute_swpb, None,                     ), # 10xx | 080
        'RRA'  : (0x22, msp_fmt2.execute_rra,  None,                     ), # 10xx | 100
        'SXT'  : (0x23, msp_fmt2.execute_sxt,  None,                     ), # 10xx | 180
        'PUSH' : (0x24, msp_fmt2.execute_push, msp_fmt2.writefields_push,), # 10xx | 200
        'CALL' : (0x25, msp_fmt2.execute_call, msp_fmt2.writefields_call,), # 10xx | 280
        'RETI' : (0x26, msp_fmt2.execute_reti, msp_fmt2.writefields_reti,), # 10xx | 300
    },
    'smodes' : {
    #    smode     n  mk_readfields                   writefields                   a_bitval r_bitval
        'Rn'    : (0, msp_fmt2.mk_readfields_src_Rn,  msp_fmt2.writefields_src_Rn,  0,       None,),
        'X(Rn)' : (2, msp_fmt2.mk_readfields_src_idx, msp_fmt2.writefields_src_idx, 1,       None,),
        'ADDR'  : (2, msp_fmt2.mk_readfields_src_sym, msp_fmt2.writefields_src_sym, 1,       0,   ),
        '&ADDR' : (2, msp_fmt2.mk_readfields_src_abs, msp_fmt2.writefields_src_abs, 1,       2,   ),
        '#1'    : (0, msp_fmt2.mk_readfields_src_cg1, msp_fmt2.writefields_src_cg1, 1,       3,   ),
        '@Rn'   : (0, msp_fmt2.mk_readfields_src_ind, msp_fmt2.writefields_src_ind, 2,       None,),
        '@Rn+'  : (0, msp_fmt2.mk_readfields_src_ai,  msp_fmt2.writefields_src_ai,  3,       None,),
        '#N'    : (0, msp_fmt2.mk_readfields_src_N,   msp_fmt2.writefields_src_N,   3,       0,   ),
    },
}

def create_fmt2(name, smode, verbosity = 0):
    opc, execute, writefields_exec = fmt2['instructions'][name]
    ins = instr.Instr(opc, fmt2['fields'], name=name, fmt='fmt2', verbosity=verbosity)

    n, mk_readfields, writefields, a_bitval, r_bitval = fmt2['smodes'][smode]
    addr.set_fmt2_src(ins, smode, n, mk_readfields, writefields, a_bitval,
                      r_bitval=r_bitval, verbosity=verbosity)

    if not writefields_exec is None:
        ins.writefields = writefields_exec
    ins.execute = execute
    return ins

jump = {
    'fields' : {
        'offset' : (0,  8, ),
        's'      : (9,  9, ),
        'cond'   : (10, 12,),
        'opc'    : (13, 15,),
    },
    'instructions' : {
    #    name    opc  cond execute                   instruction map
        'JNZ' : (0x1, 0x0, msp_jump.execute_jnz,), # 20xx
        'JZ'  : (0x1, 0x1, msp_jump.execute_jz, ), # 24xx
        'JNC' : (0x1, 0x2, msp_jump.execute_jnc,), # 28xx
        'JC'  : (0x1, 0x3, msp_jump.execute_jc, ), # 2cxx
        'JN'  : (0x1, 0x4, msp_jump.execute_jn, ), # 30xx
        'JGE' : (0x1, 0x5, msp_jump.execute_jge,), # 34xx
        'JL'  : (0x1, 0x6, msp_jump.execute_jl, ), # 38xx
        'JMP' : (0x1, 0x7, msp_jump.execute_jmp,), # 3cxx
    },
}

def create_jump(name, verbosity = 0):
    opc, cond, execute = jump['instructions'][name]
    ins = instr.Instr(opc, jump['fields'], name=name, fmt='jump', verbosity=verbosity)

    (cond_firstbit, cond_lastbit) = jump['fields']['cond']
    if verbosity >= 3:
        print('assigning cond bits')
        utils.explain_bitval(cond_firstbit, cond_lastbit, cond)
    instr.set_bitval(ins.bits, cond_firstbit, cond_lastbit, cond,
                     checkprev=True, preval='cond')

    ins.readfields = msp_jump.mk_readfields(ins)
    ins.writefields = msp_jump.writefields
    ins.execute = execute
    return ins

def create_itable(verbosity = 0):
    itable = []

    for name in sorted(fmt1['instructions']):
        for smode in sorted(fmt1['smodes']):
            for dmode in sorted(fmt1['dmodes']):
                itable.append(create_fmt1(name, smode, dmode, verbosity=verbosity))

    for name in sorted(fmt2['instructions']):
        for smode in sorted(fmt2['smodes']):
            itable.append(create_fmt2(name, smode, verbosity=verbosity))

    for name in sorted(jump['instructions']):
        itable.append(create_jump(name, verbosity=verbosity))

    return itable

# sanity test
if __name__ == '__main__':
    itab = create_itable(verbosity = 10)
    print(repr(itab))
    for ins in itab:
        print('')
        print(ins.tohex())
        ins.describe()
    print('')
    print('{:d} instructions'.format(len(itab)))
