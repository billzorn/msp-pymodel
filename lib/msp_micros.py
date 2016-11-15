import traceback

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
                        yield [(name, smode, dmode, rsrc, rdst, bw)] * (i+2)
    for name in iter_fmt2_ins():
        for smode, rsrc in iter_fmt1_src():
            for bw in [0, 1]:
                for i in range(n):
                    yield [(name, smode, 'none', rsrc, -1, bw)] * (i+2)
    for name in iter_jump_ins():
        for bw in [0, 1]:
            for i in range(n):
                yield [(name, 'none', 'none', -1, -1, bw)] * (i+2)

# recover wishlist entry from instruction
def micro_description(ins, fields):
    if 'rsrc' in fields:
        rsrc = fields['rsrc']
    else:
        rsrc = -1
    if 'rdst' in fields:
        rdst = fields['rdst']
    else:
        rdst = -1
    if 'bw' in fields:
        bw = fields['bw']
    elif 'jump_taken' in fields:
        taken = fields['jump_taken']
        if taken:
            bw = 0
        else:
            bw = 1
    else:
        bw = -1
    return ins.name, ins.smode, ins.dmode, rsrc, rdst, bw

# Now we need to actually generate micros

def valid_readable_address(addr):
    return (isinstance(addr, int) 
            and ((model.ram_start <= addr and addr < model.ram_start + model.ram_size)
                 or (model.fram_start <= addr and addr < model.fram_start + model.fram_size)))

def valid_writable_address(addr):
    return (isinstance(addr, int) 
            and (model.ram_start <= addr and addr < model.ram_start + model.ram_size))

def valid_sr_bits(i):
    return isinstance(i, int) and i & ((~271) & 0xfffff) == 0

def validator_if_needed(needed, x):
    if needed is True or needed == 'pc':
        def validate(y):
            return y == x
    elif needed == 'sr':
        def validate(y):
            if y == x or valid_sr_bits(y):
                return True
    elif needed is False or needed is None:
        def validate(y):
            return True
    else:
        print(needed)
        assert False
    return validate

# Helpers to provide safe source values for PC/SR operations.
# Assumes carry bit is 0. Go read the description of the SUBC instruction
# to see why the correct value is -1.
def get_fmt1_identity(name):
    if   name in {'MOV', 'DADD'}:
        return None
    elif name in {'ADD', 'ADDC', 'SUB', 'BIC', 'BIS', 'XOR'}:
        return 0
    elif name in {'SUBC', 'AND'}:
        return 0xffff #TODO: only 16 bits
    else:
        raise ValueError('no fmt1 identity: {:s}'.format(name))

def is_fmt1_identity(name, x):
    try:
        identity_value = get_fmt1_identity(name)
    except ValueError:
        return False
    if identity_value is None:
        return False
    else:
        return x == identity_value

def prep_jump(info, name, taken):

    testname = 'test_{:s}_{:s}_{:s}'.format(name, 'taken' if taken else 'nottaken', unique_id())

    if taken:
        if   name == 'JNZ':            
            sr = 0x0
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JZ':
            sr = 0x2
            setup = [('MOV', '#N', 'Rn', {'isrc':0x2, 'rdst':2, 'bw':0})]
        elif name == 'JNC':
            sr = 0x0
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JC':
            sr = 0x1
            setup = [('MOV', '#N', 'Rn', {'isrc':0x1, 'rdst':2, 'bw':0})]
        elif name == 'JN':
            sr = 0x4
            setup = [('MOV', '#N', 'Rn', {'isrc':0x4, 'rdst':2, 'bw':0})]
        elif name == 'JGE':
            sr = 0x0
            setup = [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JL':
            sr = 0x100
            setup = [('MOV', '#N', 'Rn', {'isrc':0x100, 'rdst':2, 'bw':0})]
        elif name == 'JMP':
            sr = None
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
            sr = 0x2
            setup += [('MOV', '#N', 'Rn', {'isrc':0x2, 'rdst':2, 'bw':0})]
        elif name == 'JZ':
            sr = 0x0
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JNC':
            sr = 0x1
            setup += [('MOV', '#N', 'Rn', {'isrc':0x1, 'rdst':2, 'bw':0})]
        elif name == 'JC':
            sr = 0x0
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JN':
            sr = 0x0
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JGE':
            sr = 0x100
            setup += [('MOV', '#N', 'Rn', {'isrc':0x100, 'rdst':2, 'bw':0})]
        elif name == 'JL':
            sr = 0x0
            setup += [('MOV', '#N', 'Rn', {'isrc':0x0, 'rdst':2, 'bw':0})]
        elif name == 'JMP':
            raise ValueError('condition: cannot have a non-taken unconditional JMP')
        else:
            raise ValueError('Not a jump instruction: {:s}'.format(repr(name)))
        
        bench = [(name, 'none', 'none', {'s':     ('JSIGN',  testname + '_FAIL'),
                                         'offset':('JLABEL', testname + '_FAIL')})]
    
    if sr is not None:
        info.check_or_set_use(2, validator_if_needed(True, sr), sr)
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
    saddr = 0x1d00
    daddr = 0x1d10

    # will be updated if we need it for part of an address
    simm = 0x1d20
    dimm = 0x1d30

    # guaranteed to be used as data, changed to labels for call
    sval = 0x1d40
    dval = 0x1d50
    # We WILL end up throwing this into the reginfo, even if it is written to some address
    # somewhere.
    # Also, note that it might become something fun like ('LABEL', 'longstring'),
    # but that shouldn't be a problem.

    # flags to indicate whether exact data is needed
    require_source_data = None
    generate_post_label = False

    # autoincrement mode might change the value in the source register, even when it's
    # being used as an address
    ai_src_offset = 0
    if smode in {'@Rn+'}:
        ai_src_offset = 1
        if rsrc == 1 or bw == 0:
            ai_src_offset = 2
    # if the destination register is the same as the source register, it
    # will be incremented as well.
    ai_dst_offset = 0
    if rsrc == rdst:
        ai_dst_offset = ai_src_offset

    # First, handle some special cases for fmt2
    if name in {'PUSH', 'CALL'}:
        known_daddr = info.check_or_set_use(1, valid_writable_address, daddr)
        # look at what's in the stack pointer; we'll use it for writing some stuff
        if known_daddr is False:
            setup.append(('MOV', '#N', 'Rn', {'isrc':daddr, 'rdst':1, 'bw':0}))
        else:
            daddr = known_daddr
        # of course we'll actually write at daddr-2, but we record daddr here to
        # represent the value in the register. we'll check if daddr-2 is still a
        # valid address later.
    if name in {'CALL'}:
        assert not require_source_data
        sval = ('LABEL', testname + '_POST')
        require_source_data = 'pc'
        generate_post_label = True
    if name in {'RETI'}:
        # this seems to be the standard encoding
        if not (smode == 'Rn' and rsrc == 0):
            raise ValueError('condition: {:s} {:s} R{:d} unsupported, use {:s} Rn R0'
                             .format(name, smode, rsrc, name))
        # We need to be sure nobody is using R1 at all, otherwise a PUSH
        # instruction that we've already decided to emit could throw everything
        # way off. Unfortunately this prevents us from testing multiple
        # in a row.
        if info.conflict(1) is False:
            # we can just use daddr-4 because we know that nothing will be put in between
            # our setup instructions, and the net effect is to put daddr-4 in the SP.
            # quick check to make sure the addresses are legal though.
            assert (valid_writable_address(daddr-2) and
                    valid_writable_address(daddr-4))
            info.add(uses={1:daddr-4,
                           daddr-2:('LABEL', testname + '_POST'),
                           daddr-4:0})
            setup += [
                ('MOV', '#N', 'Rn', {'isrc':daddr, 'rdst':1, 'bw':0}),
                ('PUSH', '#N', 'none', {'isrc':('LABEL', testname + '_POST'), 'bw':0}),
                ('PUSH', 'Rn', 'none', {'rsrc':3, 'bw':0}),
            ]
            generate_post_label = True
        else:
            raise ValueError('conflict: already using R1, cannot reserve for RETI.')
    if name in {'SWPB', 'SXT', 'CALL', 'RETI'} and bw == 1:
        # undefined behavior
        raise ValueError('condition: {:s} bw=1 unsupported'.format(name))

    # We do the destination mode for fmt1 before the source mode, as it might determine
    # what has to go in sval (for example, if our destination is PC or SR)
    if   dmode in {'Rn'}:
        # right now we can't support general PC arithmetic...
        if rdst in {0} and name not in {'MOV', 'CMP', 'BIT'}:
            raise ValueError('condition: {:s} to PC unsupported (hardware diverges if previous instruction is PUSH!)'
                             .format(name))
        if rdst in {0, 2}:
            # we still want to assert even if we don't need to set a specific source value
            assert not require_source_data
            # MOV has no identity, we need to special case in a label
            if name in {'MOV'}:
                if rdst == 0:
                    sval = ('LABEL', testname + '_POST')
                    generate_post_label = True
                    require_source_data = 'pc'
                else:
                    sval = 0
                    if name in {'MOV','BIC','BIS','CMP','BIT'}:
                        require_source_data = 'sr'
                    else:
                        require_source_data = 'pc'
            # otherwise pick a source value that will preserve the value in the register
            # after the operation
            elif assem.modifies_destination(name):
                # assume not a PC operation
                assert rdst != 0
                sval = get_fmt1_identity(name)
                assert sval is not None
                if name in {'MOV','BIC','BIS','CMP','BIT'}:
                    require_source_data = 'sr'
                else:
                    require_source_data = 'pc'
        elif rdst in {3}:
            # don't bother trying to set r3; do we need any kind of check here?
            pass
        elif info.check_or_set_use(rdst, validator_if_needed(False, dval), dval) is False:
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
            # try to use offset to separate locations
            dimm = 0x2
            daddr = saddr + 0x2
        else:
            # remember new address
            daddr = known_daddr
        # if we will change rdst due to rsrc==rdst ai, then use the modified address
        daddr_post_ai = (daddr + ai_dst_offset) & -2
        if valid_writable_address(daddr_post_ai):
            if info.check_or_set_use(daddr_post_ai,
                                     validator_if_needed(False, dval), 
                                     dval) is False:
                setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr_post_ai, 'bw':0}))
        else:
            info.check_or_set_use(daddr_post_ai,
                                  validator_if_needed(require_source_data, dval),
                                  None)        
    elif dmode in {'ADDR'}:
        dimm = ('PC_ABS', daddr)
        if info.check_or_set_use(daddr, validator_if_needed(False, dval), dval) is False:
            assert valid_writable_address(daddr)
            setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr, 'bw':0}))
    elif dmode in {'&ADDR'}:
        dimm = daddr
        if info.check_or_set_use(daddr, validator_if_needed(False, dval), dval) is False:
            assert valid_writable_address(daddr)
            setup.append(('MOV', '#N', '&ADDR', {'isrc':dval, 'idst':daddr, 'bw':0}))
    elif dmode in {'none'}:
        pass
    else:
        assert False, 'unexpected address usage in dmode? {:s} {:d}'.format(dmode, rdst)

    # Next, do setup for source mode, including addressing and value
    if   smode in {'Rn'}:
        # we can't control the PC value
        if rsrc in {0}:
            if not validator_if_needed(require_source_data, sval)(None):
                raise ValueError('condition: PC holds wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
            else:
                sval = None
        # we might be able to control the SR value, currently not well supported though
        elif rsrc in {2}:
            v = info.conflict(2)
            if v is False or v is True:
                v = None
            if not validator_if_needed(require_source_data, sval)(v):
                raise ValueError('condition: SR holds wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
            else:
                sval = v
        elif assem.has_cg(smode, rsrc) or assem.has_cg(smode, rsrc) == 0:
            cg_value = assem.has_cg(smode, rsrc)
            if not validator_if_needed(require_source_data, sval)(cg_value):
                raise ValueError('condition: CG provides wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
            else:
                sval = cg_value
        else:
            known_sval = info.check_or_set_use(rsrc, 
                                               validator_if_needed(require_source_data, sval), 
                                               sval)
            if known_sval is False:
                setup.append(('MOV', '#N', 'Rn', {'isrc':sval, 'rdst':rsrc, 'bw':0}))
            else:
                sval = known_sval
            assert rsrc != 3, 'really?'

    elif smode in {'X(Rn)'}:
        assert rsrc not in {0, 2, 3}, 'invalid source mode: {:s} {:d}'.format(smode, rsrc)
        if name in {'PUSH', 'CALL'} and rsrc in {1}:
            raise ValueError('condition: {:s} X(SP) unsupported'
                             .format(name))
        # for now, move into the register, and use 0 offset...
        known_saddr = info.check_or_set_use(rsrc, valid_readable_address, saddr)
        simm = 0
        if known_saddr is False:
            setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
        else:
            # remember new address
            saddr = known_saddr

        check_sval = sval if valid_writable_address(saddr) else None
        known_sval = info.check_or_set_use(saddr,
                                           validator_if_needed(require_source_data, sval), 
                                           check_sval)
        if known_sval is False and valid_writable_address(saddr):
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
        else:
            sval = known_sval

    elif smode in {'ADDR'}:
        simm = ('PC_ABS', saddr)
        
        known_sval = info.check_or_set_use(saddr, 
                                           validator_if_needed(require_source_data, sval), 
                                           sval)
        if known_sval is False:
            assert valid_writable_address(saddr)
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
        else:
            sval = known_sval

    elif smode in {'&ADDR'}:
        simm = saddr
        known_sval = info.check_or_set_use(saddr, 
                                           validator_if_needed(require_source_data, sval), 
                                           sval)
        if known_sval is False:
            assert valid_writable_address(saddr)
            setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
        else:
            sval = known_sval

    elif smode in {'@Rn', '@Rn+'}:
        assert rsrc not in {0}, 'invalid source mode: {:s} {:d}'.format(smode, rsrc)
        if name in {'PUSH', 'CALL'} and rsrc in {1}:
            raise ValueError('condition: {:s} @SP{:s} unsupported'
                             .format(name, '+' if smode in {'@Rn+'} else ''))
        cg_value = assem.has_cg(smode, rsrc)
        if cg_value is not None:
            if not validator_if_needed(require_source_data, sval)(cg_value):
                raise ValueError('condition: CG provides wrong value for {:s} {:s} R{:d}'
                                 .format(name, smode, rsrc))
            else:
                sval = cg_value
        else:
            known_saddr = info.check_or_set_use(rsrc, valid_readable_address, saddr)
            if known_saddr is False:
                setup.append(('MOV', '#N', 'Rn', {'isrc':saddr, 'rdst':rsrc, 'bw':0}))
            else:
                saddr = known_saddr
                
            check_sval = sval if valid_writable_address(saddr) else None
            known_sval = info.check_or_set_use(saddr,
                                               validator_if_needed(require_source_data, sval), 
                                               check_sval)
            if known_sval is False and valid_writable_address(saddr):
                setup.append(('MOV', '#N', '&ADDR', {'isrc':sval, 'idst':saddr, 'bw':0}))
            else:
                sval = known_sval

            # we need to do something here if we're autoincrementing
            if   ai_src_offset == 1:
                # to support this we need to emit .b moves in setup code...
                info.overwrite_or_set_use(rsrc, None)
            elif ai_src_offset == 2:
                info.overwrite_or_set_use(rsrc, saddr + ai_src_offset)

    elif smode in {'#@N', '#N'}:
        simm = sval

    elif smode in {'#1'}:
        if not validator_if_needed(require_source_data, sval)(1):
            raise ValueError('condition: CG provides wrong value for {:s} {:s} R{:d}'
                             .format(name, smode, rsrc))
        else:
            sval = 1

    else:
        assert False, 'unexpected smode? {:s} R{:d}'.format(smode, rsrc)

    # Finally, we have to take into account what happens to the destination after we execute the
    # instruction.
    
    actual_dmode = dmode
    actual_rdst = rdst
    # if we're getting the address out of a register, need to check for ai shenanigans
    actual_daddr = daddr
    if actual_dmode in {'X(Rn)'}:
        actual_daddr = (actual_daddr + ai_dst_offset) & -2

    # whitelist some fmt2 instructions that behave like they have a destination
    if name in {'RRC', 'SWPB', 'RRA', 'SXT'}:
        actual_dmode = smode
        actual_rdst = rsrc
        actual_daddr = saddr
        if not valid_writable_address(actual_daddr):
            raise ValueError('conflict: cannot use source addr {:05x} to write destination of {:s}'
                             .format(actual_daddr, name))
        # some fmt2 instructions have modes that are not well defined by the manual
        if actual_dmode in {'#1', '#N', '#@N'} or assem.has_cg(actual_dmode, actual_rdst):
            raise ValueError('condition: unsupported mode {:s} R{:d} for {:s}'
                             .format(actual_dmode, actual_rdst, name))

    if actual_dmode in {'Rn'}:
        # make sure value being put into destination is acceptable
        if actual_rdst in {0, 2}:
            if assem.modifies_destination(name) and actual_rdst in {0} and bw == 1:
                raise ValueError('condition: must use bw=0 when operating on PC')
            if name in {'MOV'}:
                if rdst == 0:
                    if not sval == ('LABEL', testname + '_POST'):
                        raise ValueError('condition: bad source value {:s} for {:s} {:s} R{:d}'
                                         .format(repr(sval), name, actual_dmode, actual_rdst))
                else:
                    if not valid_sr_bits(sval):
                        raise ValueError('condition: bad source value {:s} for {:s} {:s} R{:d}'
                                         .format(repr(sval), name, actual_dmode, actual_rdst))
                    else:
                        info.overwrite_or_set_use(actual_rdst, sval)
            elif assem.modifies_destination(name):
                # this isn't really used for the PC nowadays anyway...
                if not is_fmt1_identity(name, sval):
                    # clever hack because BIS and BIC can't cause a carry
                    if actual_rdst in {2} and name in {'BIS', 'BIC'} and valid_sr_bits(sval):
                        assert actual_rdst == 2
                    else:
                        raise ValueError('condition: bad source value {:s} for {:s} {:s} R{:d}'
                                         .format(repr(sval), name, actual_dmode, actual_rdst))
                # If we're carry dependent, also need to look at the value in the SR.
                if name in {'ADDC', 'SUBC'}:
                    if info.check_or_set_use(2, 
                                             validator_if_needed(True, 0),
                                             0) is False:
                        setup.append(('MOV', 'Rn', 'Rn', {'rsrc':3, 'rdst':2, 'bw':0}))
                # and if we are doing a byte operation on SR, we'll clear the high bits...
                if actual_rdst in {2}:
                    dval = info.conflict(actual_rdst)

                    if isinstance(sval, int) and isinstance(dval, int):
                        if name in {'BIC'}:
                            dval = (~sval) & dval
                        elif name in {'BIS'}:
                            dval = sval | dval
                    else:
                        dval = None

                    if bw == 1 and isinstance(dval, int):
                        dval = dval & 0xff

                    info.overwrite_or_set_use(actual_rdst, dval)

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

    if assem.modifies_sr(name):
        info.overwrite_or_set_use(2, None)
        info.add(clobbers=[2])

    # hack, instructions that modify the SP update the value afterwards
    if name in {'PUSH', 'CALL'}:
        offset = -2
        
        # check if the offest we picked looks writable
        spval = info.conflict(1)
        if not (isinstance(spval, int) and valid_writable_address(spval + offset)):
            raise ValueError('conflict: SP appears to hold invalid stack address: {:s} + {:s}'
                             .format(repr(spval), repr(offset)))
        
        # record the new value for the SP
        info.overwrite_or_set_use(1, spval + offset)
        # and destroy the data where we're writing
        info.overwrite_or_set_use(spval + offset, None)
    # or destroy it in the case of RETI. we can write manual benchmarks to handle multiple in a row
    if name in {'RETI'}:
        info.overwrite_or_set_use(1, None)

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
    if generate_post_label:
        bench.append(testname + '_POST')

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

    # debug HACK
    # for x in setup + bench:
    #     if isinstance(x, tuple):
    #         name, smode, dmode, fields = x
    #         if name == 'MOV' and dmode == '&ADDR' and not(valid_writable_address(fields['idst'])):
    #             print(setup)
    #             print(bench)
    #             assert False

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
def iter_states(codes_iterator, measure = True, verbosity = 0, metrics = None):
    start_addr = model.fram_start
    end_addr = model.ivec_start - 256
    haltpad = 8
    size = end_addr - start_addr - (haltpad*2)

    header_region = emit_init(start_timer = measure)
    header_size = assem.region_size(header_region)

    current_addr = start_addr
    current_region = []
    current_size = 0

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
                    #traceback.print_exc()
                elif str(e).startswith('conflict'):
                    conflict_failures += 1
                    # print(codes)
                    # traceback.print_exc()
                else:
                    if verbosity >= 2:
                        traceback.print_exc()
                    other_failures += 1
            continue
        except Exception as e:
            if verbosity >= 1:
                if verbosity >= 2:
                    traceback.print_exc()
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
            for i in range(haltpad-1):
                write16(start_pc + header_size + current_size + (i*2), 0x3fff)
            write16(start_pc + header_size + current_size + ((haltpad-1)*2), 0x3ff8)
            # ram
            for i in range(256):
                write16(model.ram_start + (i*2), 0x3fff)
            # resetvec
            write16(model.resetvec, start_pc)
            yield state

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
        start_pc = current_addr
        if start_pc % 2 == 1:
            start_pc += 1

        words = assem.assemble_symregion(header_region + current_region, start_pc)
        assert len(words) * 2 == header_size + current_size

        state = model.Model()
        write16 = model.mk_write16(state.write8)
        for i in range(start_pc - start_addr):
            state.write8(start_addr + i, 0)
        for i in range(len(words)):
            write16(start_pc + (i*2), words[i])
        # halt
        for i in range(haltpad-1):
            write16(start_pc + header_size + current_size + (i*2), 0x3fff)
        write16(start_pc + header_size + current_size + ((haltpad-1)*2), 0x3ff8)
        # ram
        for i in range(256):
            write16(model.ram_start + (i*2), 0x3fff)
        # resetvec
        write16(model.resetvec, start_pc)
        yield state

    if verbosity >= 1:
        print('{:d} successes, {:d} conflicts, {:d} unsupported, {:d} errors'
              .format(successes, conflict_failures, condition_failures, other_failures))
    if metrics is not None:
        metrics.append((successes, conflict_failures, condition_failures, other_failures))

if __name__ == '__main__':
    import sys
    import traceback

    codes = [('AND', 'Rn', 'Rn', 4, 2, 0),
             ('MOV', '@Rn', 'Rn', 4, 2, 1)]

    code = emit_micro(0, codes)
    for x in code:
        print(x)
    exit(0)

    n = int(sys.argv[1])
    good = 0
    bad = 0
    err = 0

    for codes in iter_reps(n):
        # if codes[0][0] not in {'CALL'}:
        #     continue
        # print('-- {:s} --'.format(repr(codes)))
        try:
            code = emit_micro(0, codes)
            for instr_data in code:
                print(repr(instr_data))
            words = assem.assemble_symregion(code, 0x4400, {'HALT_FAIL':0x4000})
            utils.printhex(words)
        except ValueError as e:
            if str(e).startswith('condition'):
                print('unsupported')
                bad += 1
            elif str(e).startswith('conflict'):
                traceback.print_exc()
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
