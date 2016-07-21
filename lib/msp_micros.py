import utils
import msp_assem as assem
import msp_itable as itab
import msp_fr5969_model as model
from msp_isa import isa

# so we can make unique strings
idnum = 0
def unique_id():
    global idnum
    idnum += 1
    return 'id' + str(idnum)

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
        'HALT_FAIL',                                       # label
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

def iter_fmt2_ins():
    for name in sorted(itab.fmt2['instructions']):
        yield name

def iter_jump_ins():
    for name in sorted(itab.jump['instructions']):
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
            for name in iter_fmt2_ins():
                # should be the same for both
                for smode, rsrc in iter_fmt1_src():
                    for bw in [0, 1]:
                        yield e + [(name, smode, 'none', rsrc, -1, bw)]
            for name in iter_jump_ins():
                # here bw is actually taken
                for bw in [0, 1]:
                    yield e + [(name, 'none', 'none', -1, -1, bw)]

def iter_offset(n):
    for name in iter_fmt1_ins():
        # should prolly not just copy pasta this thing everywhere
        for smode, rsrc in iter_fmt1_src():
            for dmode, rdst in iter_fmt1_dst():
                for bw in [0, 1]:
                    for i in range(n):
                        yield (([('MOV', 'Rn', 'Rn', 3, 3, 0)] * (n+1)) # NOP
                               + [(name, smode, dmode, rsrc, rdst, bw)])
    for name in iter_fmt2_ins():
        for smode, rsrc in iter_fmt1_src():
            for bw in [0, 1]:
                for i in range(n):
                    yield (([('MOV', 'Rn', 'Rn', 3, 3, 0)] * (n+1)) # NOP
                           + [(name, smode, 'none', rsrc, -1, bw)])
    for name in iter_jump_ins():
        for bw in [0, 1]:
            for i in range(n):
                yield (([('MOV', 'Rn', 'Rn', 3, 3, 0)] * (n+1)) # NOP
                       + [(name, 'none', 'none', -1, -1, bw)])

def iter_reps(n):
    for name in iter_fmt1_ins():
        # should prolly not just copy pasta this thing everywhere
        for smode, rsrc in iter_fmt1_src():
            for dmode, rdst in iter_fmt1_dst():
                for bw in [0, 1]:
                    for i in range(n):
                        yield [(name, smode, dmode, rsrc, rdst, bw)] * (i+1)
    for name in iter_fmt2_ins():
        for smode, rsrc in iter_fmt1_src():
            for bw in [0, 1]:
                for i in range(n):
                    yield [(name, smode, 'none', rsrc, -1, bw)] * (i+1)
    for name in iter_jump_ins():
        for bw in [0, 1]:
            for i in range(n):
                yield [(name, 'none', 'none', -1, -1, bw)] * (i+1)

# Now we need to actually generate micros

def valid_readable_address(addr):
    return (isinstance(addr, int) 
            and ((model.ram_start <= addr and addr < model.ram_start + model.ram_size)
                 or (model.fram_start <= addr and addr < model.fram_start + model.fram_size)))

def valid_writable_address(addr):
    return (isinstance(addr, int) 
            and (model.ram_start <= addr and addr < model.ram_start + model.ram_size))

def validator_if_needed(needed, x):
    if needed:
        def validate(y):
            return y == x
    else:
        def validate(y):
            return True
    return validate

# Helpers to provide safe source values for PC/SR operations
#def

def prep_jump(info, name, taken):

    testname = 'test_{:s}_{:s}_{:s}'.format(name, 'taken' if taken else 'nottaken', unique_id())

    if taken:
        if   name == 'JNZ':
            info.add(uses={2:0x0})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JZ':
            info.add(uses={2:0x2})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x2, 'rdst':2, 'bw':0})]
        elif name == 'JNC':
            info.add(uses={2:0x0})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JC':
            info.add(uses={2:0x1})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x1, 'rdst':2, 'bw':0})]
        elif name == 'JN':
            info.add(uses={2:0x4})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x4, 'rdst':2, 'bw':0})]
        elif name == 'JGE':
            info.add(uses={2:0x0})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JL':
            info.add(uses={2:0x100})
            setup = [('MOV', '#N', 'Rn', {'isrc':0x100, 'rdst':2, 'bw':0})]
        elif name == 'JMP':
            setup = []
        else:
            raise ValueError('Not a jump instruction: {:s}'.format(repr(name)))

        bench = [
            (name, 'none', 'none', {'s':0, 'offset':2}),                           # jump being measured
            ('MOV', '#N', 'Rn', {'isrc':('LABEL','HALT_FAIL'), 'rdst':0, 'bw':0}), # goto fail
        ]

    else: # not taken
        setup = [
            ('JMP', 'none', 'none',  {'s':0, 'offset':2}),                         # jump over fail
            testname + '_FAIL',                                                    # label
            ('MOV', '#N', 'Rn', {'isrc':('LABEL','HALT_FAIL'), 'rdst':0, 'bw':0}), # goto fail
        ]
        if   name == 'JNZ':
            info.add(uses={2:0x2})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x2, 'rdst':2, 'bw':0})]
        elif name == 'JZ':
            info.add(uses={2:0x0})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JNC':
            info.add(uses={2:0x1})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x1, 'rdst':2, 'bw':0})]
        elif name == 'JC':
            info.add(uses={2:0x0})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JN':
            info.add(uses={2:0x0})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JGE':
            info.add(uses={2:0x100})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x100, 'rdst':2, 'bw':0})]
        elif name == 'JL':
            info.add(uses={2:0x0})
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JMP':
            raise ValueError('condition: cannot have a non-taken unconditional JMP')
        else:
            raise ValueError('Not a jump instruction: {:s}'.format(repr(name)))
        
        bench = [(name, 'none', 'none', {'s':     ('JSIGN',  testname + '_FAIL'),
                                         'offset':('JLABEL', testname + '_FAIL')})]

    return setup, bench

# Generate necessary setup conditions and state dependencies
def prep_instruction(info, name, smode, dmode, rsrc, rdst, bw):

    testname = ('test_{:s}_{:s}_{:s}_{:d}_{:d}_{:s}'
                .format(name, smode, dmode, rsrc, rdst, unique_id()))
    
    setup = []
    fmt = isa.name_to_fmt[name]

    # special logic for jump instructions
    if fmt == 'jump':
        return prep_jump(info, name, (bw == 0))
    
    # hard coded
    saddr = 0x1c00
    daddr = 0x1c10

    # will be updated if we need it for part of an address
    simm = 0x1c20
    dimm = 0x1c30

    # guaranteed to be used as data, changed to labels for call
    sval = 0x1c40
    dval = 0x1c50
    # We WILL end up throwing this into the reginfo, even if it is written to some address
    # somewhere.
    # Also, note that it might become something fun like ('LABEL', 'longstring'),
    # but that shouldn't be a problem.

    # flags to indicate whether exact data is needed
    require_source_data = False

    # First, handle some special cases for fmt2
    if name in {'PUSH', 'CALL'}:
        if info.check_or_set_use(1, valid_writable_address, daddr) is False:
            setup += [('MOV', '#N', 'Rn', {'isrc':daddr, 'rdst':1, 'bw':0})]
    elif name in {'CALL'}:
        sval = ('LABEL', testname + '_CALL')
        require_source_data = True
    elif name in {'RETI'}:
        raise ValueError('condition: {:s} unsupported'.format(name))
        #TODO implement these
    elif name in {'SWPB', 'SXT'} and bw == 1:
        raise ValueError('condition: {:s} bw=1 unsupported'.format(name))
        # undefined behavior

    # We do the destination mode for fmt1 before the source mode, as it might determine
    # what has to go in sval (for example, if our destination is PC or SR)
    if   dmode in {'Rn'}:
        # if rsrc in {0}:
        #     assert not require_source_data
        #     # TODO: force the right value into sval
        #     require_source_data = True
        # elif rsrc in {2}:
        #     assert not require_source_data
        #     # TODO: force the right value into sval
        #     require_source_data = True
        if info.check_or_set_use(rdst, validator_if_needed(False, dval), dval):
            setup.append(('MOV', '#N', 'Rn', {'isrc':dval, 'rdst':rdst, 'bw':0}))
    elif dmode in {'X(Rn)'}:
        assert rdst not in {0, 2, 3}, 'invalid destination mode: {:s} {:d}'.format(smode, rdst)
        # get the value in the register
        known_daddr = info.check_or_set_use(rdst, valid_writable_address, daddr)
        dimm = 0x0
        # if it's not already set, set it, otherwise we might be able to be clever
        if known_daddr is False:
            setup.append(('MOV', '#N', 'Rn', {'isrc':daddr, 'rdst':rdst, 'bw':0}))
        elif known_daddr == saddr:
            dimm = 0x2
            daddr = saddr + 0x2
        else:
            # remember new address
            daddr = known_daddr
        if info.check_or_set_use(daddr, validator_if_needed(False, dval), dval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr, 'bw':0}))
    elif dmode in {'ADDR'}:
        dimm = ('PC_ABS', daddr)
        if info.check_or_set_use(daddr, validator_if_needed(False, dval), dval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr, 'bw':0}))
    elif dmode in {'&ADDR'}:
        dimm = daddr
        if info.check_or_set_use(daddr, validator_if_needed(False, dval), dval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr, 'bw':0}))
    elif dmode in {'none'}:
        pass
    else:
        assert False, 'unexpected address usage in dmode? {:s} {:d}'.format(dmode, rdst)

    # Next, do setup for source mode, including addressing and value
    if   smode in {'Rn'}:
        if rsrc in {0}:
            if not validator_if_needed(require_source_data, sval)(None):
                raise ValueError('condition: PC holds wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
        elif rsrc in {2}:
            v = info.conflict([2])
            if v is False or v is True:
                v = None
            if not validator_if_needed(require_source_data, sval)(v):
                raise ValueError('condition: SR holds wrong vaalue for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
        else:
            if info.check_or_set_use(rsrc, 
                                     validator_if_needed(require_source_data, sval), 
                                     sval) is False:
                # We look at the current value, and if it needs to be something specific and already
                # isn't, we fail. Otherwise if it wasn't set, we set it.
                setup.append(('MOV', '#N', 'Rn', {'isrc':sval, 'rdst':rsrc, 'bw':0}))
    elif smode in {'X(Rn)'}:
        assert rsrc not in {0, 2, 3}, 'invalid source mode: {:s} {:d}'.format(smode, rsrc)
        # for now, move into the register, and use 0 offset...
        known_saddr = info.check_or_set_use(rsrc, valid_readable_address, saddr)
        simm = 0
        if known_saddr is False:
            setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
        else:
            # remember new address
            saddr = known_saddr
        if info.check_or_set_use(saddr, 
                                 validator_if_needed(require_source_data, sval), 
                                 sval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
    elif smode in {'ADDR'}:
        simm = ('PC_ABS', saddr)
        if info.check_or_set_use(saddr, 
                                 validator_if_needed(require_source_data, sval), 
                                 sval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
    elif smode in {'&ADDR'}:
        simm = saddr
        if info.check_or_set_use(saddr, 
                                 validator_if_needed(require_source_data, sval), 
                                 sval) is False:
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
    elif smode in {'@Rn', '@Rn+'}:
        assert rsrc not in {0}, 'invalid source mode: {:s} {:d}'.format(smode, rsrc)
        cg_value = assem.has_cg(smode, rsrc)
        if cg_value is not None:
            if not validator_if_needed(require_source_data, sval)(cg_value):
                raise ValueError('condition: CG provides wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
        else:
            known_saddr = info.check_or_set_use(rsrc, valid_readable_address, saddr)
            if known_saddr is False:
                setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
            else:
                # remember new address
                saddr = known_saddr
            if info.check_or_set_use(saddr,
                                     validator_if_needed(require_source_data, sval),
                                     sval) is False:
                setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
    elif smode in {'#@N', '#N'}:
        simm = sval
    elif smode in {'#1'}:
        if not validator_if_needed(require_source_data, sval)(1):
            raise ValueError('condition: CG provides wrong value for {:s} {:s} R{:d}'
                             .format(name, smode, rsrc))
    else:
        assert False, 'unexpected smode? {:s} R{:d}'.format(smode, rsrc)

    # Finally, we have to take into account what happens to the destination after we execute the
    # instruction.
    
    actual_dmode = dmode
    actual_rdst = rdst
    actual_daddr = daddr
    # whitelist some fmt2 instructions that behave like they have a destination
    if name in {'RRC', 'SWPB', 'RRA', 'SXT'}:
        actual_dmode = smode
        actual_rdst = rsrc
        actual_daddr = daddr
        # some fmt2 instructions have modes that are not well defined by the manual
        if actual_dmode in {'#1', '#N', '#@N'} or assem.has_cg(actual_dmode, actual_rdst):
            raise ValueError('condition: unsupported mode {:s} R{:d} for {:s}'
                             .format(actual_dmode, actual_rdst, name))

    if actual_dmode in {'Rn'}:
        # make sure value being put into destination is acceptable
        if actual_rdst == 2: # status register
            if name not in {'CMP', 'BIT'}:
                raise ValueError('condition: dest mode not safe for SR: {:s} {:d}'
                                 .format(actual_dmode, actual_rdst))
        elif actual_rdst == 0: # pc
            if not name in {'CMP', 'BIT'}:
                raise ValueError('condition: dest mode not safe for PC: {:s} {:d}'
                                 .format(actual_dmode, actual_rdst))
        # just stubs for now

        # Otherwise add destination register to clobbers since we're writing to it.
        # I think this is all we need to do.
        else:
            info.overwrite_or_set_use(actual_rdst, None)
            # by default, just clobber the register and claim that it holds None,
            # which is basically a placeholder for undefined. In general we could
            # figure out what value will actually be there after executing the
            # instruction, but that isn't supported yet.
            info.add(clobbers=[actual_rdst])
    elif assem.uses_addr(actual_dmode, actual_rdst):
        # trust that the address we have is correct
        info.overwrite_or_set_use(actual_daddr, None)
        info.add(clobbers=[actual_daddr])
    elif actual_dmode in {'none'}:
        pass
    else:
        assert False, 'unexpected apparent dmode? {:s} R{:d}'.format(actual_dmode, actual_rdst)

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

    bench = [(name, smode, dmode, fields)]
    if name in {'CALL'}:
        bench.append(testname + '_CALL')

    return setup, bench

# addr is the base pc at which the text of this micro will start
# codes is a list of instructions to put in between the measurements:
# (name, smode, dmode, rsrc, rdst, bw)
def emit_micro(addr, codes, measure=True):
    timer_r1 = 14
    timer_r2 = 15

    # record dependencies: will need to be strengthened
    # Also, for reasons that appear to me to be a major bug in Python3, if you don't pass
    # the explicit intial empty uses and clobbers, uses will magically contain {14:None}
    # when the Reginfo object is created, and all hell will break loose.
    info = assem.Reginfo(uses={}, clobbers=[])
    
    # sequences to emit
    measure_pre = []
    setup = []
    bench = []
    measure_post = []

    if measure:
        info.add(uses={timer_r1:None}, clobbers=[timer_r1])
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
        info.add(uses={timer_r2:None}, clobbers=[timer_r2, 2])
        measure_post += emit_timer_read_rn(timer_r2)
        measure_post += emit_timer_compute_store(timer_r1, timer_r2, addr)

    teardown = []
    # reset all registers that might have unknown state
    for rn in info.clobbers:
        if 0 <= rn and rn < model.reg_size:
            teardown.append(('MOV', 'Rn', 'Rn', {'rsrc':3, 'rdst':rn, 'bw':0}))
        else:
            teardown.append(('MOV', 'Rn', '&ADDR', {'rsrc':3, 'idst':rn, 'bw':0}))

    return setup + measure_pre + bench + measure_post + teardown

# pack up executables from the provided generator of instruction codes
def iter_states(codes_iterator, measure = True, verbosity = 0):
    start_addr = model.fram_start
    end_addr = model.ivec_start - 256
    size = end_addr - start_addr

    header_region = emit_init(start_timer = measure)
    header_size = assem.region_size(header_region)

    current_addr = start_addr
    current_region = []
    current_size = 0
    states = []

    condition_failures = 0
    conflict_failures = 0
    other_failures = 0
    successes = 0

    for codes in codes_iterator:
        try:
            region = emit_micro(current_addr, codes, measure=measure)
        except ValueError as e:
            if verbosity >= 1:
                if str(e).startswith('condition'):
                    condition_failures += 1
                elif str(e).startswith('conflict'):
                    conflict_failures += 1
                else:
                    if verbosity >= 2:
                        print(e)
                    other_failures += 1
            continue
        except Exception as e:
            if verbosity >= 1:
                if verbosity >= 2:
                    print(2)
                other_failures += 1
            continue

        successes += 1

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

            # increment, so we don't accidentally reuse the start_addr again
            current_addr += 1

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

    if verbosity >= 1:
        print('{:d} successes, {:d} conflicts, {:d} unsupported, {:d} errors'
              .format(successes, conflict_failures, condition_failures, other_failures))

    return states


if __name__ == '__main__':
    import sys
    import traceback
    n = int(sys.argv[1])

    good = 0
    bad = 0
    err = 0

    for codes in iter_to_depth(n):
        print('-- {:s} --'.format(repr(codes)))
        try:
            code = emit_micro(0, codes)
            # for instr_data in code:
            #     print(repr(instr_data))
            # words = assem.assemble_symregion(code, 0x4400, {'HALT_FAIL':0x4000})
            # utils.printhex(words)
        except ValueError as e:
            traceback.print_exc()
            if str(e).startswith('condition'):
                bad += 1
            elif str(e).startswith('conflict'):
                bad += 1
            else:
                err += 1
        except Exception as e:
            traceback.print_exc()
            err += 1
        else:
            good += 1
        print('')

    print('good: {:d}, bad: {:d}, err: {:d}'.format(good, bad, err))
