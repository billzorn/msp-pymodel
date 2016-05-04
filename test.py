#!/usr/bin/env python3

import sys
import os
import random

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

from msp_isa import isa
import msp_itable as itab
import msp_fr5969_model as model
import msp_elftools as elftools

scratch_start = 0x1c00
scratch_end   = 0x2400
scratch_size  = scratch_end - scratch_start
storage_start = 0x4400
storage_end   = 0x6000
storage_size  = storage_end - storage_start
prog_start = 0x6000
prog_end   = 0xf000
prog_size  = prog_end - prog_start

r_imm_state = 0
def r_imm():
    global r_imm_state
    r_imm_state += 1
    return r_imm_state
    #return random.randint(0, 65535)

def r_addr():
    return random.randint(scratch_start, scratch_end-1)

def has_immediate(mode):
    if mode in {'X(Rn)', 'ADDR', '&ADDR', '#N'}:
        return True
    elif mode in {'Rn', '#1', '@Rn', '@Rn+'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def uses_addr(mode):
    if mode in {'X(Rn)', 'ADDR', '&ADDR', '@Rn', '@Rn+'}:
        return True
    elif mode in {'Rn', '#1', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))

def uses_reg(mode):
    if mode in {'Rn', 'X(Rn)', '@Rn', '@Rn+'}:
        return True
    elif mode in {'ADDR', '&ADDR', '#1', '#N'}:
        return False
    else:
        raise ValueError('not an addressing mode: {:s}'.format(mode))
        

def assemble(fmt, name, smode, dmode, fields):
    ins = isa.modes_to_instr(fmt, name, smode, dmode)
    words = isa.inhabitant(ins, fields)
    return words

def mov_iaddr(i, addr):
    return assemble('fmt1', 'MOV', '#N', '&ADDR', {'isrc':i, 'idst':addr, 'bw':0})

def mov_irn(i, rn):
    return assemble('fmt1', 'MOV', '#N', 'Rn', {'isrc':i, 'rdst':rn, 'bw':0})

# put stuff into the register so that we hit this address
def setup_mode(mode, rn, addr):
    addr = addr
    if mode in {'X(Rn)'}:
        # split address between register and immediate
        reg_part = random.randint(0, addr-1)
        addr_part = addr - reg_part
        assert(reg_part >=0 and addr_part >= 0 and reg_part + addr_part == addr)
        return addr_part, mov_irn(reg_part, rn)
    elif mode in {'@Rn', '@Rn+'}:
        # set the register
        return addr, mov_irn(addr, rn)
    else:
        return addr, []

def emit_read_timer(rn):
    return assemble('fmt1', 'MOV', '&ADDR', 'Rn', {'isrc':0x350, 'rdst':rn, 'bw':0})

def emit_compute_store_timer(r1, r2, addr):
    return (assemble('fmt1', 'SUB', 'Rn', 'Rn', {'rsrc':r1, 'rdst':r2, 'bw':0}) +
            assemble('fmt1', 'MOV', 'Rn', '&ADDR', {'rsrc':r2, 'idst':addr, 'bw':0}))

def emit_disable_watchdog():
    return mov_iaddr(23168, 0x015c)

def emit_timer_start():
    return (mov_iaddr(16, 0x0342) +
            mov_iaddr(512, 0x0340) +
            mov_iaddr(0, 0x0350) +
            mov_iaddr(50000, 0x352) +
            assemble('fmt1', 'BIS', '#N', '&ADDR', {'isrc':16, 'idst':0x0340, 'bw':0}))

def emit_fmt1(name, smode, dmode, rsrc, rdst, old_pc):
    if rsrc in {0, 2, 3} and not smode in {'Rn'}:
        raise ValueError('{:s} r{:s}: bad idea'.format(smode, rsrc))

    saddr, ssetup = setup_mode(smode, rsrc, r_addr())
    daddr, dsetup = setup_mode(dmode, rdst, r_addr())
    words = ssetup + dsetup
    pc = old_pc + (len(words) * 2)

    ins = isa.modes_to_instr('fmt1', name, smode, dmode)
    pc = pc + ins.length

    # need to do very special things for the pc
    if rdst == 0:
        assert(False)
        
    # fix addresses for pc-relative addressing
    if smode in {'ADDR'}:
        saddr = (saddr - pc) & 0xffff
    if dmode in {'ADDR'}:
        daddr = (daddr - pc) & 0xffff

    # note that we haven't done anything to change the value that starts
    # in the register if it's data (Rn mode), we'll just use whatever's there and
    # it's fine

    # we do need to choose a random immediate for #N mode though
    if smode in {'#N'}:
        saddr = r_imm() # bad variable names, ehh

    fields = {'bw':random.randint(0,1)}

    if uses_reg(smode):
        fields['rsrc'] = rsrc
    if has_immediate(smode):
        fields['isrc'] = saddr
    if uses_reg(dmode):
        fields['rdst'] = rdst
    if has_immediate(dmode):
        fields['idst'] = daddr
    ins_words = isa.inhabitant(ins, fields)

    # print()
    # print(hex(old_pc))
    # print(smode, dmode, rsrc, rdst)
    # ins.describe()
    # print(repr(fields))
    # print([hex(w) for w in ins_words])

    return words + ins_words

# word based
def init_scratch(size):
    return [r_imm() for _ in range(size // 2)]
def init_storage(size):
    return [0 for _ in range(size // 2)]

def gen():
    scratch_words = init_scratch(scratch_size)
    storage_words = init_storage(storage_size)

    trn_1 = 14
    trn_2 = 15

    old_pc = prog_start
    store = storage_start
    words = emit_disable_watchdog() + emit_timer_start()
    for name in itab.fmt1['instructions']:
    #for name in ['ADD']:
        if name not in {'DADD'}:
            for smode in itab.fmt1['smodes']:
                for dmode in itab.fmt1['dmodes']:
                    for rsrc in [0,1,2,3,4]:
                        for rdst in [5]:
                            try:
                                pc = old_pc
                                # t1_words = emit_read_timer(trn_1)
                                # pc += len(t1_words)
                                fmt1_words = emit_fmt1(name, smode, dmode, rsrc, rdst, pc)
                                pc += len(fmt1_words)
                                # t2_words = emit_read_timer(trn_2)
                                # store_words = emit_compute_store_timer(trn_1, trn_2, store)
                                # pc += len(t2_words) + len(store_words)
                            except ValueError as e:
                                print(e)
                            else:
                                #store += 2
                                old_pc = pc
                                #words += t1_words + fmt1_words + t2_words + store_words
                                words += fmt1_words

    assert(old_pc < prog_end and store < storage_end)

    # create the model
    state = model.Model()
    write16 = model.mk_write16(state.write8)
    for i in range(len(scratch_words)):
        write16(scratch_start + (i*2), scratch_words[i])
    for i in range(len(storage_words)):
        write16(storage_start + (i*2), storage_words[i])
    for i in range(len(words)):
        write16(prog_start + (i*2), words[i])
    # halt
    for i in range(8):
        write16(prog_start + (len(words)*2) + (i*2), 0x3fff)
    # reset
    write16(model.resetvec, prog_start)
    return state

    

if __name__ == '__main__':

    # for i in range(len(isa.ids_ins)):
    #     ins = isa.idx_to_instr(i)
    #     modes = isa.idx_to_modes(i)
    #     print(modes)
    #     print(ins.live_fields())
    
    # fields = {'rsrc':7, 'rdst':15, 'bw':0}

    # for smode in itab.fmt1['smodes']:
    #     for dmode in itab.fmt1['dmodes']:
    #         print(smode, dmode)
    #         ins = isa.modes_to_instr('fmt1', 'CMP', smode, dmode)
    #         ins.describe()
            
    #         f = fields.copy()
    #         if has_immediate(smode):
    #             f['isrc'] = 17777
    #         if has_immediate(dmode):
    #             f['idst'] = 0x4400

    #         print(f)
    #         words = isa.inhabitant(ins, f)
    #         print(ins.live_fields())
    #         print(words)
    
    tname = sys.argv[1]
    state = gen()
    state.dump()
    elftools.save(state, tname)
            
