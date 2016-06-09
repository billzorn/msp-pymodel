import msp_assem as assem
import msp_itable as itab
import msp_fr5969_model as model

# There are several ways to perform a timer read:
# First, we can read to a register. This has the least overhead,
# but does cost us the register until we do something with it.
# For micros where we can control the available register set,
# the tightest wrapping is:

# SETUP ...
# MOV &0x0350, RX
# MICRO ...
# MOV &0x0350, RY
# SUB RX, RY
# MOV RY, &0xXXXX
# CLEANUP ...

# Of course, the SUB and final MOV can be replaced with whatever
# processing and storage is appropriate

# The most general thing to do is to save the value of the timer
# in memory, restoring any registers we clobber in the process.
# The drawback here is that we'll end up "benchmarking" some of the
# instructions that we have to emit to perform the timer read, which
# restricts what possible benchmarks we can measure (because they'll
# all end with the same suffix).

# MICRO ...
# MOV RX, &.save
# MOV &.store_addr, RX
# MOV &0x0350, 0(RX)
# ADD #2, RX
# MOV RX, &.store_addr
# MOV &.save, RX
# MICRO ...

# Here, everything up to the read MOV from &0x0350 will be timed
# as a suffix of the micro. Everything after that read will be
# a prefix of the next micro, as well.

# If some of the registers can be controlled, the process could be 
# simplified by loading the timer into a free register initially, then
# doing whatever processing later. Note that this doesn't matter a
# whole lot if the measurement is immediately followed by another micro.

# Since we can't autoincrement a destination (only a source), we can't
# keep store_addr in a register and repeatedly store the timer to the 
# address in that register. We can however get by with a single add
# instruction and the store:

# MICRO ...
# (ADD #2 RT) ; option 1
# MOV &0x0350, 0(RT)
# (ADD #2 RT) ; option 2
# MICRO ...

# Again, we could also put in an intermediate load to a register
# instead of storing the timer directly.

def emit_init(start_timer=True):
    instructions = [
        # disable watchdog
        ('MOV', '#N',   '&ADDR', {'isrc':0x5a80, 'idst':0x015c, 'bw':0}),
        ('JMP', 'none', 'none',  {'s':0, 'offset':1}),     # jump over halt
        ('JMP', 'none', 'none',  {'s':1, 'offset':0x3ff}), # halt to indicate failure
    ]
    if start_timer:
        instructions += [
            # start timer
            ('MOV', '#N', '&ADDR', {'isrc':0x10,  'idst':0x0342, 'bw':0}),
            ('MOV', '#N', '&ADDR', {'isrc':0x200, 'idst':0x0340, 'bw':0}),
            ('MOV', 'Rn', '&ADDR', {'rsrc':3,     'idst':0x0350, 'bw':0}), # cg 0
            ('MOV', '#N', '&ADDR', {'isrc':50000, 'idst':0x0352, 'bw':0}),
            ('BIS', '#N', '&ADDR', {'isrc':0x10,  'idst':0x0340, 'bw':0}),
        ]
    return instructions

def emit_timer_read_rn(rn):
    return [('MOV', '&ADDR', 'Rn', {'isrc':0x0350, 'rdst':rn, 'bw':0})]

def emit_timer_compute_store(r1, r2, addr):
    return [
        ('SUB', 'Rn', 'Rn',    {'rsrc':r1, 'rdst':r2, 'bw':0}),
        ('MOV', 'Rn', '&ADDR', {'rsrc':r2, 'idst':addr, 'bw':1}),
    ]

# Brute force iteration over all 'interesting' instruction combinations.
# The machine basically has 5 registers (R0/PC, R1/SP, R2/SR, R3, R4-R15),
# 4 source addressing modes (as is 2 bits), 2 destination addressing modes
# (ad is 1 bit), 2 bit widths (byte/word), and some number of instructions.
# If we're clever, and we're willing to run overnight, we can probably test
# all pairs of interesting instructions exhaustively. We can then switch to
# random testing to try and make sure that everything still works for longer
# sequences and for other registers / memory locations.

def iter_fmt1_src():
    # easier to just transcribe the table by hand:
    
    #        R0(PC)  R1(SP)  R2(SR)  R3      R4-R15
    # Rn     ok!     ok!     ok!     = 0     ok!
    # X(Rn)  ADDR    ok!     &ADDR   ##1 ?2  ok!
    # @Rn    #@N     ok!     ##4     ##2     ok!
    # @Rn+   #N      ok! ?1  ##8     ##-1    ok!
    
    # ?1: The stack pointer always increments by 2 in autoincrement
    #     mode, even with a byte instruction (bw=1) like MOV.B, etc.
    # ?2: Note that this is its own unique addressing mode because
    #     it normally has an immediate, but not when used in this CG
    #     mode.

    for basemode in ('Rn', 'X(Rn)', '@Rn', '@Rn+'):
        for reg in (0, 1, 2, 3, 4):
           
            # detect special modes
            mode = basemode
            if basemode == 'X(Rn)':
                if reg == 0:
                    mode = 'ADDR'
                elif reg == 2:
                    mode = '&ADDR'
                elif reg == 3:
                    mode = '#1'
            elif basemode == '@Rn':
                if reg == 0:
                    mode = '#@N'
            elif basemode == '@Rn+':
                if reg == 0:
                    mode = '#N'
            
            yield mode, reg

def iter_fmt1_dst():
    # this table is smaller:

    #        R0(PC)  R1(SP)  R2(SR)      R3      R4-R15
    # Rn     = PC    ok!     &0x30=0 ?1  = 0     ok!
    # X(Rn)  ADDR    ok!     &ADDR       XXX ?2  ok!

    # Obviously, if you write the PC, then the machine will start
    # executing from wherever you wrote, or something like that.

    # ?1: Don't set bits 4 or 5 (0x30) of the SR, as these are 
    #     OSC_OFF and CPU_OFF. Probably don't set any of the other
    #     bits either, besides 0-2 and 8. And don't do it with
    #     instructions other than BIS. But eh, what's the worst
    #     that can happen?
    # ?2: Using X(R3) as a destination does not do the expected
    #     thing (which would be to act like &ADDR mode and read
    #     0 from the register). It does something, but I haven't figured
    #     out exactly what yet.

    for basemode in ['Rn', 'X(Rn)']:
        for reg in (0, 1, 2, 3, 4):
            
            mode = basemode
            if basemode == 'X(Rn)':
                if reg == 0:
                    mode = 'ADDR'
                elif reg == 2:
                    mode = '&ADDR'
                elif reg == 3:
                    # could do something here someday
                    continue
            
            yield mode, reg

def iter_fmt1_ins():
    for name in sorted(itab.fmt1['instructions']):
        if name not in {'DADD'}:
            yield name

def iter_to_depth(n):
    if n <= 0:
        yield []
    else:
        for e in iter_to_depth(n-1):
            # here's the massive ugly thingy
            for name in iter_fmt1_ins():
                for smode, rsrc in iter_fmt1_src():
                    for dmode, rdst in iter_fmt1_dst():
                        for bw in [0, 1]:
                            yield e + [(name, smode, dmode, rsrc, rdst, bw)]
            # fmt2 and jumps will have to go here...


# Now we need to actually generate micros

# Generate necessary setup conditions and state dependencies
def prep_instruction(info, name, smode, dmode, rsrc, rdst, bw):
    
    setup = []
    
    # hard coded
    saddr = 0x1c00
    daddr = 0x1c02

    # will be updated if we need it for part of an address
    simm = 0x7777
    dimm = 0x8888

    # set up addressing for source mode
    if assem.uses_addr(smode, rsrc):
        if smode in {'X(Rn)'}:
            # could do something more intelligent and try to compute a valid offset
            # from a known value of the register
            assert rsrc not in {0, 2, 3}, 'invalid source mode: {:s} {:d}'.format(smode, rsrc)
            info.add(uses=[rsrc])
            # for now, move into the register, and use 0 offset...
            setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
            simm = 0
        elif smode in {'ADDR'}:
            simm = ('PC_ABS', saddr) # assembler will resolve at assembly time
        elif smode in {'&ADDR'}:
            simm = saddr
        elif smode in {'@Rn', '@Rn+'}:
            assert rsrc not in {2, 3}, 'not an indirect mode? {:s} {:d}'.format(smode, rsrc)
            # it is probably ok to leave the pc alone here; we can read from it usually
            if rsrc != 0:
                info.add(uses=[rsrc])
                # move address into register
                setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
        else:
            assert False, 'unexpected address usage in smode? {:s} {:d}'.format(smode, rsrc)

    # set up addressing for destination mode
    if assem.uses_addr(dmode, rdst):
        if dmode in {'X(Rn)'}:
            assert rdst not in {0, 2, 3}, 'invalid destination mode: {:s} {:d}'.format(smode, rdst)
            # this is ugly
            if info.conflict([rdst]):
                if rsrc == rdst:
                    # we know the conflict was from this (otherwise we'd have hit a conflict
                    # while setting up the source)
                    dimm = 0x2 # we know rdst holds saddr, this gets us to daddr
                else:
                    raise ValueError('conflict: unable to set or determine value in register {:d}'
                                     .format(rdst))
            else:
                info.add(uses=[rdst])
                setup.append(('MOV', '#N', 'Rn', {'isrc':daddr, 'rdst':rdst, 'bw':0}))
                dimm = 0
        elif dmode in {'ADDR'}:
            dimm = ('PC_ABS', daddr) # let assembler resolve
        elif dmode in {'&ADDR'}:
            dimm = daddr
        else:
            assert False, 'unexpected address usage in dmode? {:s} {:d}'.format(dmode, rdst)

    # make sure value being put into destination is acceptable
    if dmode == 'Rn' and rdst == 2: # status register
        if name not in {'CMP', 'BIT'}:
            raise ValueError('condition: source mode not safe for SR: {:s} {:d}'
                             .format(smode, rsrc))
    if dmode == 'Rn' and rdst == 0: # pC
        if not name in {'CMP', 'BIT'}:
            raise ValueError('condition: source mode not safe for PC: {:s} {:d}'
                             .format(smode, rsrc))
    # just stubs for now

    # prepare fields
    fields = {'bw':bw}
    if assem.has_reg(smode):
        fields['rsrc'] = rsrc
    if assem.has_immediate(smode):
        # check
        assert not (smode == 'X(Rn)' and rsrc == 3), 'no immediate: {:s} {:d}'.format(smode, rsrc)
        fields['isrc'] = simm
    if assem.has_reg(dmode):
        fields['rdst'] = rdst
    if assem.has_immediate(dmode):
        fields['idst'] = dimm

    return setup, [(name, smode, dmode, fields)]

# addr is the base pc at which the text of this micro will start
# codes is a list of instructions to put in between the measurements:
# (name, smode, dmode, rsrc, rdst, bw)
def emit_micro(addr, codes, measure=True):
    timer_r1 = 14
    timer_r2 = 15

    # record dependencies: will need to be strengthened
    info = assem.Reginfo()

    # sequences to emit... computing pc relative addresses is going to be gross
    measure_pre = []
    setup = []
    bench = []
    measure_post = []

    if measure:
        info.add(uses=[timer_r1], clobbers=[timer_r1])
        measure_pre += emit_timer_read_rn(timer_r1)

    # the tricky things are:
    #  1) making sure that we don't try to access invalid addresses
    #  2) making sure we obey the destination conditions for R0 and R2
    
    # This is mostly hard because we might have dependencies:
    # MOV #1, R4
    # MOV @R4, R4 ; whelp

    for name, smode, dmode, rsrc, rdst, bw in codes:
        local_setup, local_bench = prep_instruction(info, name, smode, dmode, rsrc, rdst, bw)
        setup += local_setup
        bench += local_bench

    if measure:
        info.add(uses=[timer_r2], clobbers=[timer_r2, 2])
        measure_post += emit_timer_read_rn(timer_r2)
        measure_post += emit_timer_compute_store(timer_r1, timer_r2, addr)

    teardown = []
    # reset all registers that might have unknown state
    for rn in info.clobbers:
        teardown.append(('MOV', 'Rn', 'Rn', {'rsrc':3, 'rdst':rn, 'bw':0}))

    return measure_pre + setup + bench + measure_post + teardown

# pack up executables from the provided generator of instruction codes
def iter_states(codes_iterator, measure = True):
    start_addr = model.fram_start
    end_addr = model.ivec_start - 16
    size = end_addr - start_addr

    header_region = emit_init(start_timer = measure)
    header_size = assem.region_size(header_region)

    current_addr = start_addr
    current_region = []
    current_size = 0
    states = []

    for codes in codes_iterator:
        try:
            region = emit_micro(current_addr, codes, measure=measure)
        except ValueError:
            continue

        rsize = assem.region_size(region)
        start_pc = current_addr
        if start_pc % 2 == 1:
            start_pc += 1

        if header_size + current_size + (start_pc - start_addr) > size:
            words = assem.assemble_symregion(header_region + current_region, start_pc)
            assert len(words) * 2 == header_size + current_size

            state = model.Model()
            write16 = model.mk_write16(state.write8)
            for i in range(start_pc - start_addr):
                state.write8(start_addr + i, 0)
            for i in range(len(words)):
                write16(start_pc + (i*2), words[i])
            # halt
            for i in range(8):
                write16(start_pc + header_size + current_size + (i*2), 0x3fff)
            # ram
            write16(0x1c00, 0x5555)
            write16(0x1c02, 0xaaaa)
            # resetvec
            write16(model.resetvec, start_pc)
            states.append(state)

            current_addr = start_addr

            # recalculate, so we get the first addr right for the next state
            region = emit_micro(current_addr, codes, measure=measure)
            rsize = assem.region_size(region)

            current_region = region
            current_size = rsize

        else:
            current_addr += 1
            current_region += region
            current_size += rsize

    if len(current_region) > 0:
        words = assem.assemble_symregion(header_region + current_region, start_pc)
        assert len(words) * 2 == header_size + current_size

        state = model.Model()
        write16 = model.mk_write16(state.write8)
        for i in range(start_pc - start_addr):
            state.write8(start_addr + i, 0)
        for i in range(len(words)):
            write16(start_pc + (i*2), words[i])
        # halt
        for i in range(8):
            write16(start_pc + header_size + current_size + (i*2), 0x3fff)
        # ram
        write16(0x1c00, 0x5555)
        write16(0x1c02, 0xaaaa)
        # resetvec
        write16(model.resetvec, start_pc)
        states.append(state)

    return states


if __name__ == '__main__':
    good = 0
    bad = 0
    err = 0

    for codes in iter_to_depth(2):
        print('-- {:s} --'.format(repr(codes)))
        try:
            emit_micro(0, codes)
        except ValueError as e:
            print(e)
            if str(e).startswith('condition'):
                bad += 1
            elif str(e).startswith('conflict'):
                bad += 1
            else:
                err += 1
        except Error as e:
            print(e)
            err += 1
        else:
            good += 1
        print('')

    print('good: {:d}, bad: {:d}, err: {:d}'.format(good, bad, err))
