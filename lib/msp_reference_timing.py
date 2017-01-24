# from TI documentation SLAU367L, p 132-133

import msp_assem as assem

def reference_time(ins, fields):
    if ins.fmt in {'fmt1'}:
        # assume CG counts as register source
        if ins.smode in {'Rn', '#1'} or assem.has_cg(ins.smode, fields['rsrc']):
            if ins.dmode in {'Rn'}:
                cycles = 1
                # ERRATA 1: the 2 cycle overhead does NOT apply to non-writing instructions!
                if fields['rdst'] == 0 and ins.name not in {'CMP', 'BIT'}:
                    cycles = 3
            else:
                cycles = 4
        elif ins.smode in {'@Rn', '@Rn+', '#N', '#@N'}:
            if ins.dmode in {'Rn'}:
                cycles = 2
                # ERRATA 1: the 2 cycle overhead does NOT apply to non-writing instructions!
                if fields['rdst'] == 0 and ins.name not in {'CMP', 'BIT'}:
                    # assume fake #@N mode is like #N mode
                    if ins.smode in {'#N', '#@N'}:
                        cycles = 3
                    else:
                        cycles = 4
            else:
                cycles = 5
        else: # ins.smode in {'X(Rn)', 'ADDR', '&ADDR'}
            if ins.dmode in {'Rn'}:
                cycles = 3
                # ERRATA 1: the 2 cycle overhead does NOT apply to non-writing instructions!
                if fields['rdst'] == 0 and ins.name not in {'CMP', 'BIT'}:
                    cycles = 5
            else:
                cycles = 6

        # implement footnote for MOV, BIT, CMP w/ ad=1
        if ins.name in {'MOV', 'BIT', 'CMP'} and ins.dmode in {'X(Rn)', 'ADDR', '&ADDR'}:
            assert cycles >= 4
            cycles -= 1

    # always assume CG counts as register source, even where it should never be allowed
    elif ins.fmt in {'fmt2'}:
        if ins.name in {'RETI'}:
            cycles = 5

        elif ins.name in {'CALL'}:
            if ins.smode in {'Rn', '@Rn', '@Rn+', '#N', '#@N', '#1'} or assem.has_cg(ins.smode, fields['rsrc']):
                cycles = 4
            elif ins.smode in {'X(Rn)', 'ADDR'}:
                cycles = 5
            else: # ins.smode in {'&ADDR'}
                #cycles = 6
                # ERRATA 2: this is actually 5 cycles in the 1 d1 micro that hits it...
                # changing between 5 and 6 has no effect on rep4 errors
                cycles = 5

        elif ins.name in {'PUSH'}:
            if ins.smode in {'Rn', '@Rn', '@Rn+', '#N', '#@N', '#1'} or assem.has_cg(ins.smode, fields['rsrc']):
                cycles = 3
            else: # ins.smode in {'X(Rn)', 'ADDR', '&ADDR'}
                cycles = 4

        else: # ins.name in {'RRA', 'RRC', 'SWPB', 'SXT'}
            if ins.smode in {'Rn', '#1'} or assem.has_cg(ins.smode, fields['rsrc']):
                cycles = 1
            elif ins.smode in {'@Rn', '@Rn+'}:
                cycles = 3
            # documentation specifically says N/A
            elif ins.smode in {'#N', '#@N'}:
                cycles = None
            else: # ins.smode in {'X(Rn)', 'ADDR', '&ADDR'}
                cycles = 4
            
    elif ins.fmt in {'jump'}:
        cycles = 2

    # unknown format
    else:
        cycles = None

    return cycles
