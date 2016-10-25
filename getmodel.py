# analyzer / generator for historical models

import sys
import os
import pickle

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

from msp_isa import isa
import smt
import historical_models

def is_valid_mode(ins, rsname, rdname):
    source_valid = True
    dest_valid = True

    if ins.fmt in {'fmt1', 'fmt2'}:
        if ins.smode in {'Rn'}:
            source_valid = True
        elif ins.smode in {'X(Rn)'}:
            source_valid = rsname not in {smt.smt_rnames[0], smt.smt_rnames[2], smt.smt_rnames[3]}
        elif ins.smode in {'ADDR'}:
            source_valid = rsname in {smt.smt_rnames[0]}
        elif ins.smode in {'&ADDR'}:
            source_valid = rsname in {smt.smt_rnames[2]}
        elif ins.smode in {'#1'}:
            source_valid = rsname in {smt.smt_rnames[3]}
        elif ins.smode in {'@Rn'}:
            source_valid = rsname not in {smt.smt_rnames[0]}
        elif ins.smode in {'#@N'}:
            source_valid = rsname in {smt.smt_rnames[0]}
        elif ins.smode in {'@Rn+'}:
            source_valid = rsname not in {smt.smt_rnames[0]}
        elif ins.smode in {'#N'}:
            source_valid = rsname in {smt.smt_rnames[0]}
        else:
            raise ValueError('smode??? {:s}'.format(ins.smode))

    if ins.fmt in {'fmt1'}:
        if ins.dmode in {'Rn'}:
            dest_valid = True
        elif ins.dmode in {'X(Rn)'}:
            dest_valid = rdname not in {smt.smt_rnames[0], smt.smt_rnames[2], smt.smt_rnames[3]}
        elif ins.dmode in {'ADDR'}:
            dest_valid = rdname in {smt.smt_rnames[0]}
        elif ins.dmode in {'&ADDR'}:
            dest_valid = rdname in {smt.smt_rnames[2]}
        elif ins.dmode in {'#1'}:
            dest_valid = rdname in {smt.smt_rnames[3]}
        else:
            raise ValueError('dmode??? {:s}'.format(ins.dmode))

    return source_valid and dest_valid

def is_supported_instruction(ins, rsname, rdname):
    if ins.fmt == 'fmt1':
        if ins.name in {'DADD'}:
            raise ValueError('DADD - bad')
        elif ins.dmode in {'#1'} and rdname in {smt.smt_rnames[3]}:
            raise ValueError('bad destination for fmt1: {:s} {:s} {:s}'
                             .format(ins.name, ins.dmode, rdname))
        elif rsname == smt.smt_rnames[-1] or rdname == smt.smt_rnames[-1]:
            raise ValueError('bad registers for fmt1: {:s} {:s}'.format(rsname, rdname))
        elif ins.dmode in {'Rn'} and rdname in {smt.smt_rnames[0], smt.smt_rnames[2]}:
            # constant generator
            if ins.smode in {'@Rn', '@Rn+'} and rsname in {smt.smt_rnames[2], smt.smt_rnames[3]}:
                return ins.name in {'CMP', 'BIT'}
            elif ins.smode in {'#1'} and rsname in {smt.smt_rnames[3]}:
                return ins.name in {'CMP', 'BIT'}
            # PCSR
            elif ins.smode in {'Rn'} and rsname in {smt.smt_rnames[0], smt.smt_rnames[2]}:
                return ins.name in {'CMP', 'BIT'}
            elif ins.smode in {'Rn'} and rsname in {smt.smt_rnames[3]}:
                if rdname in {smt.smt_rnames[0]}:
                    return ins.name in {'CMP', 'BIT'}
                else:
                    return ins.name not in {'AND', 'SUBC'}
            # remainder of PC
            elif rdname in {smt.smt_rnames[0]}:
                return ins.name in {'CMP', 'BIT', 'MOV'}
        return True
    elif ins.fmt == 'fmt2':
        if rsname == smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]:
            raise ValueError('bad registers for fmt2: {:s} {:s}'.format(rsname, rdname))
        elif ins.name in {'RETI'}:
            return ins.smode == 'Rn' and rsname == smt.smt_rnames[0]
        elif ins.name in {'CALL', 'PUSH'}:
            if rsname == smt.smt_rnames[1] and ins.smode in {'X(Rn)', '@Rn', '@Rn+'}:
                return False
            elif ins.name in {'CALL'}:
                if (ins.smode, rsname) not in {
                        ('@Rn', smt.smt_rnames[4]),
                        ('ADDR', smt.smt_rnames[0]),
                        ('&ADDR', smt.smt_rnames[2]),
                        ('X(Rn)', smt.smt_rnames[4]),
                        ('#@N', smt.smt_rnames[0]),
                        ('@Rn', smt.smt_rnames[4]),
                        ('#N', smt.smt_rnames[0]),
                        ('@Rn+', smt.smt_rnames[4])
                }:
                    return False
            return True
        elif ins.name in {'SWPB', 'SXT', 'RRC', 'RRA'}:
            if ins.smode in {'Rn'} and rsname in {smt.smt_rnames[0], smt.smt_rnames[2]}:
                return False
            elif ins.smode in {'#1'} and rsname in {smt.smt_rnames[3]}:
                return False
            elif ins.smode in {'@Rn', '#@N', '@Rn+', '#N'} and rsname in {smt.smt_rnames[0], smt.smt_rnames[2], smt.smt_rnames[3]}:
                return False
            return True
        else:
            raise ValueError('what fmt2 is this? {:s}'.format(ins.name))
    elif ins.fmt == 'jump':
        if rsname != smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]:
            raise ValueError('bad registers for jump: {:s} {:s}'.format(rsname, rdname))
        return True
    else:
        raise ValueError('what is this? {:s} {:s}'.format(ins.fmt, ins.name))

def create_model_table_10(record, fname):
    rsrc_rdst_strings = record['time_fn_rsrc_rdst']
    state0_strings = record['state_fn_init']
    state_strings = record['state_fn_default']

    inames = {smt.smt_iname(ins) : ins for ins in isa.ids_ins}
    states = [0, 1, 2, 3]
    state_default = smt.get_state_id(state0_strings)

    rsrc_rdst_pool = set([(s, x, rs, rd)
                          for s in states
                          for x in inames
                          for rs in smt.smt_rnames.values()
                          for rd in smt.smt_rnames.values()])
    ttab = {}

    rsrc_rdst_else = None
    for arg, res in smt.split_function_string(rsrc_rdst_strings):
        if arg == ('else',):
            rsrc_rdst_else = int(res)
        else:
            (statestr, iname, rsname, rdname) = arg
            state = smt.get_state_id(statestr)
            if (state, iname, rsname, rdname) in rsrc_rdst_pool:
                rsrc_rdst_pool.remove((state, iname, rsname, rdname))
                ttab[(state, iname, rsname, rdname)] = int(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname, rsname, rdname))))
    print('rsrc_rdst_pool has {:d} remaining entries'.format(len(rsrc_rdst_pool)))
    dadds = 0
    exts = 0
    xr3s = 0
    invr = 0
    invm = 0
    unsupported = 0
    other = 0
    for x in rsrc_rdst_pool:
        state, iname, rsname, rdname = x
        ins = inames[iname]
        if ins.name == 'DADD':
            dadds += 1
            ttab[x] = None
        elif ins.fmt == 'EXT':
            exts += 1
            ttab[x] = None
        elif ins.fmt == 'fmt1' and ins.dmode == 'X(Rn)' and rdname == smt.smt_rnames[3]:
            xr3s += 1
            ttab[x] = None
        elif ins.fmt == 'jump' and (rsname != smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]):
            invr += 1
            ttab[x] = None
        elif ins.fmt == 'fmt2' and (rsname == smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]):
            invr += 1
            ttab[x] = None
        elif ins.fmt == 'fmt1' and (rsname == smt.smt_rnames[-1] or rdname == smt.smt_rnames[-1]):
            invr += 1
            ttab[x] = None
        elif not is_valid_mode(ins, rsname, rdname):
            invm += 1
            ttab[x] = None
        elif not is_supported_instruction(ins, rsname, rdname):
            unsupported += 1
            ttab[x] = None
        else:
            # print(state, ins.name, ins.smode, rsname, ins.dmode, rdname)
            # for s in states:
            #     if (s, iname, rsname, rdname) in ttab:
            #         print('  ', s, iname, rsname, rdname, ' : ', ttab[(s, iname, rsname, rdname)])                
            other += 1
            ttab[x] = None
    print('excluded {:d} dadd, {:d} ext, {:d} X(R3), {:d} invalid register, {:d} invalid mode, {:d} unsupported, {:d} other'
          .format(dadds, exts, xr3s, invr, invm, unsupported, other))

    state_pool = set([(s, x, rs, rd)
                      for s in states
                      for x in inames
                      for rs in smt.smt_rnames.values()
                      for rd in smt.smt_rnames.values()])
    stab = {}

    state_else = None
    for arg, res in smt.split_function_string(state_strings):
        if arg == ('else',):
            state_else = smt.get_state_id(res)
        else:
            (statestr, iname, rsname, rdname) = arg
            state = smt.get_state_id(statestr)
            if (state, iname, rsname, rdname) in state_pool:
                state_pool.remove((state, iname, rsname, rdname))
                stab[(state, iname, rsname, rdname)] = smt.get_state_id(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname, rsname, rdname))))
    print('state_pool has {:d} remaining entries'.format(len(state_pool)))
    dadds = 0
    exts = 0
    xr3s = 0
    invr = 0
    invm = 0
    unsupported = 0
    inf = 0
    other = 0
    for x in state_pool:
        state, iname, rsname, rdname = x
        ins = inames[iname]
        if ins.name == 'DADD':
            dadds += 1
            stab[x] = None
        elif ins.fmt == 'EXT':
            exts += 1
            stab[x] = None
        elif ins.fmt == 'fmt1' and ins.dmode == 'X(Rn)' and rdname == smt.smt_rnames[3]:
            xr3s += 1
            stab[x] = None
        elif ins.fmt == 'jump' and (rsname != smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]):
            invr += 1
            stab[x] = None
        elif ins.fmt == 'fmt2' and (rsname == smt.smt_rnames[-1] or rdname != smt.smt_rnames[-1]):
            invr += 1
            stab[x] = None
        elif ins.fmt == 'fmt1' and (rsname == smt.smt_rnames[-1] or rdname == smt.smt_rnames[-1]):
            invr += 1
            stab[x] = None
        elif not is_valid_mode(ins, rsname, rdname):
            invm += 1
            stab[x] = None
        elif not is_supported_instruction(ins, rsname, rdname):
            unsupported += 1
            stab[x] = None
        else:
            # print(state, ins.name, ins.smode, rsname, ins.dmode, rdname)
            # for s in states:
            #     if (s, iname, rsname, rdname) in stab:
            #         print('  ', s, iname, rsname, rdname, ' : ', stab[(s, iname, rsname, rdname)])
            known_transitions = set()
            for s in states:
                if (s, iname, rsname, rdname) in stab:
                    known_transitions.add(stab[s, iname, rsname, rdname])
            if known_transitions == {state_default}:
                inf += 1
                stab[x] = state_default
            else:
                other += 1
                stab[x] = None
    print('excluded {:d} dadd, {:d} ext, {:d} X(R3), {:d} invalid register, {:d} invalid mode, {:d} unsupported, {:d} inferred to initial state, {:d} other'
          .format(dadds, exts, xr3s, invr, invm, unsupported, inf, other))

    print('DONE: ttab has {:d} entries, stab has {:d} entries'
          .format(len(ttab), len(stab)))

    with open(fname, 'wb') as f:
        print('writing to {:s}'.format(fname))
        pickle.dump({'state_default':state_default, 'ttab':ttab, 'stab':stab}, f)


if __name__ == '__main__':
    fname = sys.argv[1]
    create_model_table_10(historical_models.model_m9_s10, fname)
