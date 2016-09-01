# smt bindings through z3

import pickle

import z3
z3.set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)

import utils
from msp_isa import isa

# general framework for building these "solve(blocks)" type passes

def create_block_ident(i, addr, block, difference):
    return 't_{:d}_{:05x}'.format(i, addr)

# General purpose solver loop. Define the desired behavior as functions and then pass
# them in.
#
# fn_add_constraint(s, ident, block, cycles): returns None
#   s:      the current solver
#   ident:  a unique id string for the block
#   block:  the content of the block (instructions)
#   cycles: the cycle count to execute the block
# Data is cleaned (i.e. if the diff didn't make sense, we would have already asserted)
# so the logic can go ahead and add to the solver's formula without any further checks.
# Note that if predicates are generated on the fly, the function should use some
# external data structure to keep track of them.
#
# fn_get_preds(): returns a list of z3.Bool
# This is called after all invocations of fn_add_constraint(), the idea being that
# as constraints are added, the predicates might change, so solve_x() waits until the
# last moment to ask for them.
#
# fn_process_core(core): returns True of False
#   core: an unsat core, which is a list of z3.Bool
# Maybe display information about the core, or store it somewhere. Return True to break
# out of the checker loop, or False to remove this core and continue searching for a model.
#
# returns True/False (SAT/broke out of checker loop), the final solver, remaining predicates
def solve_x(blocks, fn_add_constraint, fn_get_preds, fn_process_core, verbosity=1):
    s = z3.Solver()
    
    i = 0
    for addr, block, difference in blocks:
        ident = create_block_ident(i, addr, block, difference)
        assert len(difference) == 2 and difference[1] == 0
        cycles = difference[0]
        fn_add_constraint(s, ident, block, cycles)
        i += 1

    if verbosity >= 1:
        print('    added constraints for {:d} blocks'.format(i))

    predicates = fn_get_preds()

    if verbosity >= 1:
        print('    got {:d} control predicates, solving...'.format(len(predicates)))

    found_sat = True
    rounds = 0
    while s.check(*predicates) == z3.unsat:
        rounds += 1
        core = s.unsat_core()
        for pred in core:
            predicates.remove(pred)
        if fn_process_core(core):
            found_sat = False
            break

    if verbosity >= 1:
        print(('    found satisfying assignment' if found_sat else '    failed to find assignment')
              + ' after {:d} rounds, {:d} remaining predicates'.format(rounds, len(predicates)))

    return found_sat, s, predicates

def describe_core_cx(core, pred_blocks):
    print('-----------------------------')
    print(core)
    print('')
    for pred in core:
        ident, block, cycles = pred_blocks[pred]
        for fields in block:
            ins = isa.decode(fields['words'][0])
            fmt, name, smode, dmode = isa.instr_to_modes(ins)
            if   fmt == 'fmt1':
                rsrc = fields['rsrc']
                rdst = fields['rdst']
                if 'isrc' in fields:
                    sval = ', {:#x}'.format(fields['isrc'])
                else:
                    sval = ''
                print('{:s}\t{:s} (R{:d}{:s}), {:s} (R{:d})'
                      .format(name, smode, rsrc, sval, dmode, rdst))
            elif fmt == 'fmt2':
                rsrc = fields['rsrc']
                if 'isrc' in fields:
                    sval = ', {:#x}'.format(fields['isrc'])
                else:
                    sval = ''
                print('{:s}\t{:s} (R{:d}{:s})'
                      .format(name, smode, rsrc, sval))
            elif fmt == 'jump':
                print('{:s}\t{:d}, taken={:s}'
                      .format(name, fields['jump_offset'], str(fields['jump_taken'])))
            else:
                print('{:s}, {:s}, {:s}, {:s}'.format(fmt, name, smode, dmode))
                utils.print_dict(fields)
        print('{:d} total cycles'.format(cycles))
        print('')

def do_round_cx(blocks, mk_add_constraint, z3_data, cx_max):
    predicates = []
    pred_blocks = {}
    add_constraint = mk_add_constraint(predicates, pred_blocks, z3_data)
    def get_preds():
        return [x for x in predicates]
    cx_count = [0]
    def process_core(core):
        describe_core_cx(core, pred_blocks)
        cx_count[0] += 1
        if cx_count[0] >= cx_max:
            return True
        else:
            return False

    print('Solving for first {:d} counterexamples...'.format(cx_max))
    success, s, s_preds = solve_x(blocks,
                                  add_constraint,
                                  get_preds,
                                  process_core)

    if success:
        print('Done. Found a satisfying assignment after discarding {:d} counterexamples.'
              .format(cx_count[0]))
        for fn_object in z3_data[-1]:
            print(s.model()[fn_object])
    else:
        print('Done. Did not find a satisfying assignment after discarding {:d} counterexamples.'
              .format(cx_count[0]))
    return success, s

def do_round_instr_subset(blocks, mk_add_constraint, z3_data, ipreds):
    add_constraint = mk_add_constraint(ipreds, blacklist_std, z3_data)
    def get_preds():
        return [x for x in ipreds.values()]
    removed_pred_names = []
    cx_instrs = [0]
    def process_core(core):
        for pred in core:
            removed_pred_names.append(str(pred))
        cx_instrs[0] = cx_instrs[0] + 1
        return False

    print('Solving for largest satisfiable subset of instructions...')
    success, s, s_preds = solve_x(blocks,
                                  add_constraint,
                                  get_preds,
                                  process_core)

    print('Done. Excluded {:d} instructions across {:d} unsat cores.'
          .format(len(removed_pred_names), cx_instrs[0]))
    for pname in sorted(removed_pred_names):
        print('  ' + pname)

    if success:
        print('Found a satisfying assignment:')
        for fn_object in z3_data[-1]:
            print(s.model()[fn_object])
        print('Remaining control predicates:')
        for pname in sorted(map(str, s_preds)):
            print('  ' + pname)
    else:
        print('Did not find a satisfying assignment. {:d} control predicates remain.'
              .format(len(s_preds)))
    return success, s

# datatype definitions

def smt_iname(ins):
    if ins is None:
        return smt_iname(prev_ins)
    else:
        smode_ident = utils.mode_ident[ins.smode]
        dmode_ident = utils.mode_ident[ins.dmode]
        return '_'.join((ins.fmt, ins.name, smode_ident, dmode_ident))

def create_instr_datatype():
    Instruction = z3.Datatype('msp430_Instruction')
    for ins in isa.ids_ins:
        Instruction.declare(smt_iname(ins))
    # null instruction, for cases where an instruction is not provided or unknown
    Instruction.declare('null_instruction')
    return Instruction.create()

# filter out some instructions with known behaviors
def blacklist_std(ins, fields):
    return any([
        # read timer
        (ins.name == 'MOV' and
         ins.smode == '&ADDR' and
         ins.dmode == 'Rn' and
         fields['isrc'] == 0x0350),
        # nop
        (ins.name == 'MOV' and
         ins.smode == 'Rn' and
         ins.dmode == 'Rn' and
         fields['rsrc'] == 3 and
         fields['rdst'] == 3),
    ])

smt_rnames = {
    0 : 'PC_R0',
    1 : 'SP_R1',
    2 : 'SR_R2',
    3 : 'R3',
    4 : 'GR',
    -1 : 'Rnone',
}

def smt_rsrc(fields):
    if 'rsrc' in fields:
        r = fields['rsrc']
        if 0 <= r and r < 4:
            return smt_rnames[r]
        elif 4 <= r and r < 16:
            return smt_rnames[4]
    else:
        return smt_rnames[-1]

def smt_rdst(fields):
    if 'rdst' in fields:
        r = fields['rdst']
        if 0 <= r and r < 4:
            return smt_rnames[r]
        elif 4 <= r and r < 16:
            return smt_rnames[4]
    else:
        return smt_rnames[-1]

def create_reg_datatype():
    Register = z3.Datatype('msp430_Register')
    for rname in smt_rnames.values():
        Register.declare(rname)
    return Register.create()

def create_state_datatype(name, n):
    State = z3.Datatype('msp430_State_' + name)
    for i in range(n):
        State.declare('state_{:d}'.format(i))
    return State.create()


# smt rounds

def mk_add_constraint_individual(predicates, pred_blocks, z3_data):
    (inst_dt, time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        p = z3.Bool(ident)
        times = []
        for fields in block:
            ins = isa.decode(fields['words'][0])
            iname = smt_iname(ins)
            times.append(time_fn(inst_dt.__dict__[iname]))
        s.add(z3.Implies(p, z3.Sum(times) == cycles))
        predicates.append(p)
        if pred_blocks is not None:
            pred_blocks[p] = ident, block, cycles
    return add_constraint

def mk_add_constraint_instr(ipreds, blacklist, z3_data):
    (inst_dt, time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        preds = set()
        times = []
        for fields in block:
            ins = isa.decode(fields['words'][0])
            iname = smt_iname(ins)
            times.append(time_fn(inst_dt.__dict__[iname]))
            if blacklist is None or not blacklist(ins, fields):
                preds.add(ipreds[ins])
        s.add(z3.Implies(z3.And(*preds), z3.Sum(times) == cycles))
    return add_constraint

def round_1(blocks):
    cx_max = 5

    print('SMT timing analysis round 1.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    time_fn = z3.Function('time_r1', inst_dt, z3.IntSort())

    z3_data = (inst_dt, time_fn, [time_fn])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr, z3_data, ipreds)

def mk_add_constraint_individual_r(predicates, pred_blocks, z3_data):
    (time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        p = z3.Bool(ident)
        times = []
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields))
        s.add(z3.Implies(p, z3.Sum(times) == cycles))
        predicates.append(p)
        if pred_blocks is not None:
            pred_blocks[p] = ident, block, cycles
    return add_constraint

def mk_add_constraint_instr_r(ipreds, blacklist, z3_data):
    (time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        preds = set()
        times = []
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields))
            if blacklist is None or not blacklist(ins, fields):
                preds.add(ipreds[ins])
        s.add(z3.Implies(z3.And(*preds), z3.Sum(times) == cycles))
    return add_constraint

def round_2(blocks):
    cx_max = 5

    print('SMT timing analysis round 2.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()

    time_fn_noreg = z3.Function('time_r2_noreg', inst_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r2_rdst', inst_dt, reg_dt, z3.IntSort())
    def time_fn(ins, fields):
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and ins.dmode in {'Rn'}:
            rname = smt_rdst(fields)
            return time_fn_rdst(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        else:
            return time_fn_noreg(inst_dt.__dict__[iname])

    z3_data = (time_fn, [time_fn_noreg, time_fn_rdst])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_r, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_r, z3_data, ipreds)

def round_3(blocks):
    cx_max = 5

    print('SMT timing analysis round 3.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()

    time_fn_noreg = z3.Function('time_r3_noreg', inst_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r3_rdst', inst_dt, reg_dt, z3.IntSort())
    time_fn_rsrc = z3.Function('time_r3_rsrc', inst_dt, reg_dt, z3.IntSort())
    def time_fn(ins, fields):
        iname = smt_iname(ins)
        if   ins.fmt in {'fmt1'} and ins.dmode in {'Rn'}:
            rname = smt_rdst(fields)
            return time_fn_rdst(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        elif ins.fmt in {'fmt1'} and ins.smode in {'@Rn', '@Rn+'}:
            rname = smt_rsrc(fields)
            return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        else:
            return time_fn_noreg(inst_dt.__dict__[iname])

    z3_data = (time_fn, [time_fn_noreg, time_fn_rdst, time_fn_rsrc])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_r, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_r, z3_data, ipreds)

def round_4(blocks):
    cx_max = 5

    print('SMT timing analysis round 4.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()

    time_fn_noreg = z3.Function('time_r4_noreg', inst_dt, z3.IntSort())
    time_fn_rsrc = z3.Function('time_r4_rsrc', inst_dt, reg_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r4_rdst', inst_dt, reg_dt, z3.IntSort())
    time_fn_rsrc_rdst = z3.Function('time_r3_rsrc_rdst', inst_dt, reg_dt, reg_dt, z3.IntSort())
    def time_fn(ins, fields):
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and (ins.smode in {'@Rn', '@Rn+'} or ins.dmode in {'Rn'}):
            if   ins.smode in {'@Rn', '@Rn+'} and ins.dmode in {'Rn'}:
                rsname = smt_rsrc(fields)
                rdname = smt_rdst(fields)
                return time_fn_rsrc_rdst(inst_dt.__dict__[iname], 
                                         reg_dt.__dict__[rsname], 
                                         reg_dt.__dict__[rdname])
            elif ins.smode in {'@Rn', '@Rn+'}:
                rname = smt_rsrc(fields)
                return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
            else:
                rname = smt_rdst(fields)
                return time_fn_rdst(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        else:
            return time_fn_noreg(inst_dt.__dict__[iname])

    z3_data = (time_fn, [time_fn_noreg, time_fn_rsrc, time_fn_rdst, time_fn_rsrc_rdst])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_r, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_r, z3_data, ipreds)

def round_5(blocks):
    cx_max = 5

    print('SMT timing analysis round 5.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()

    time_fn_noreg = z3.Function('time_r5_noreg', inst_dt, z3.IntSort())
    time_fn_rsrc = z3.Function('time_r5_rsrc', inst_dt, reg_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r5_rdst', inst_dt, reg_dt, z3.IntSort())
    time_fn_rsrc_rdst = z3.Function('time_r5_rsrc_rdst', inst_dt, reg_dt, reg_dt, z3.IntSort())
    def time_fn(ins, fields):
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and (ins.smode in {'@Rn', '@Rn+'} or ins.dmode in {'Rn'}):
            if   ins.smode in {'@Rn', '@Rn+'} and ins.dmode in {'Rn'}:
                rsname = smt_rsrc(fields)
                rdname = smt_rdst(fields)
                return time_fn_rsrc_rdst(inst_dt.__dict__[iname], 
                                         reg_dt.__dict__[rsname], 
                                         reg_dt.__dict__[rdname])
            elif ins.smode in {'@Rn', '@Rn+'}:
                rname = smt_rsrc(fields)
                return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
            else:
                rname = smt_rdst(fields)
                return time_fn_rdst(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        elif ins.name in {'PUSH', 'CALL'} and ins.smode in {'X(Rn)'}:
            rname = smt_rsrc(fields)
            return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        else:
            return time_fn_noreg(inst_dt.__dict__[iname])

    z3_data = (time_fn, [time_fn_noreg, time_fn_rsrc, time_fn_rdst, time_fn_rsrc_rdst])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_r, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_r, z3_data, ipreds)

# more complex rounds that pass state of previous instructions too

def mk_add_constraint_individual_prev(predicates, pred_blocks, z3_data):
    (time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        p = z3.Bool(ident)
        times = []
        prev_ins = None
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields, prev_ins))
            prev_ins = ins
        s.add(z3.Implies(p, z3.Sum(times) == cycles))
        predicates.append(p)
        if pred_blocks is not None:
            pred_blocks[p] = ident, block, cycles
    return add_constraint

def mk_add_constraint_instr_prev(ipreds, blacklist, z3_data):
    (time_fn, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        preds = set()
        times = []
        prev_ins = None
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields, prev_ins))
            prev_ins = ins
            if blacklist is None or not blacklist(ins, fields):
                preds.add(ipreds[ins])
        s.add(z3.Implies(z3.And(*preds), z3.Sum(times) == cycles))
    return add_constraint

def round_6(blocks):
    cx_max = 5

    print('SMT timing analysis round 6.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()

    time_fn_noreg = z3.Function('time_r6_noreg', inst_dt, z3.IntSort())
    time_fn_rsrc = z3.Function('time_r6_rsrc', inst_dt, reg_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r6_rdst', inst_dt, reg_dt, z3.IntSort())
    time_fn_rsrc_rdst = z3.Function('time_r6_rsrc_rdst', inst_dt, reg_dt, reg_dt, z3.IntSort())
    time_fn_prev = z3.Function('time_r6_prev', inst_dt, inst_dt, z3.IntSort())
    def time_fn(ins, fields, prev_ins):
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and (ins.smode in {'@Rn', '@Rn+'} or ins.dmode in {'Rn'}):
            if   ins.smode in {'@Rn', '@Rn+'} and ins.dmode in {'Rn'}:
                rsname = smt_rsrc(fields)
                rdname = smt_rdst(fields)
                return time_fn_rsrc_rdst(inst_dt.__dict__[iname], 
                                         reg_dt.__dict__[rsname], 
                                         reg_dt.__dict__[rdname])
            elif ins.smode in {'@Rn', '@Rn+'}:
                rname = smt_rsrc(fields)
                return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
            else:
                rname = smt_rdst(fields)
                return time_fn_rdst(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        elif ins.name in {'PUSH', 'CALL'} and ins.smode in {'X(Rn)'}:
            rname = smt_rsrc(fields)
            return time_fn_rsrc(inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        elif ins.name in {'RRA', 'RRC', 'SWPB', 'SXT'} and ins.smode in {'@Rn', '@Rn+'}:
            pname = smt_iname(prev_ins)
            return time_fn_prev(inst_dt.__dict__[iname], inst_dt.__dict__[pname])
        else:
            return time_fn_noreg(inst_dt.__dict__[iname])

    z3_data = (time_fn, [time_fn_noreg, time_fn_rsrc, time_fn_rdst, time_fn_rsrc_rdst, time_fn_prev])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_prev, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_prev, z3_data, ipreds)

# Just reporting the previous instruction doesn't work. Let's try carrying some state along.

def mk_add_constraint_individual_state(predicates, pred_blocks, z3_data):
    (time_fn, state_fn, state_init, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        p = z3.Bool(ident)
        times = []
        z3_state = state_init()
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields, z3_state))
            z3_state = state_fn(ins, fields, z3_state)
        s.add(z3.Implies(p, z3.Sum(times) == cycles))
        predicates.append(p)
        if pred_blocks is not None:
            pred_blocks[p] = ident, block, cycles
    return add_constraint

def mk_add_constraint_instr_state(ipreds, blacklist, z3_data):
    (time_fn, state_fn, state_init, _) = z3_data
    def add_constraint(s, ident, block, cycles):
        preds = set()
        times = []
        z3_state = state_init()
        for fields in block:
            ins = isa.decode(fields['words'][0])
            times.append(time_fn(ins, fields, z3_state))
            z3_state = state_fn(ins, fields, z3_state)
            if blacklist is None or not blacklist(ins, fields):
                preds.add(ipreds[ins])
        s.add(z3.Implies(z3.And(*preds), z3.Sum(times) == cycles))
    return add_constraint

def round_7(blocks):
    cx_max = 5

    print('SMT timing analysis round 7.')

    ipreds = {ins : z3.Bool('p_' + smt_iname(ins)) for ins in isa.ids_ins}
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()
    state_dt = create_state_datatype('r7', 2)

    time_fn_noreg = z3.Function('time_r7_noreg', state_dt, inst_dt, z3.IntSort())
    time_fn_rsrc = z3.Function('time_r7_rsrc', state_dt, inst_dt, reg_dt, z3.IntSort())
    time_fn_rdst = z3.Function('time_r7_rdst', state_dt, inst_dt, reg_dt, z3.IntSort())
    time_fn_rsrc_rdst = z3.Function('time_r7_rsrc_rdst', state_dt, inst_dt, reg_dt, reg_dt, z3.IntSort())
    state_fn_default = z3.Function('state_r7_default', state_dt, inst_dt, state_dt)
    state_fn_init = z3.Function('state_r7_init', state_dt)

    def time_fn(ins, fields, state):
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and (ins.smode in {'@Rn', '@Rn+'} or ins.dmode in {'Rn'}):
            if   ins.smode in {'@Rn', '@Rn+'} and ins.dmode in {'Rn'}:
                rsname = smt_rsrc(fields)
                rdname = smt_rdst(fields)
                return time_fn_rsrc_rdst(state, 
                                         inst_dt.__dict__[iname], 
                                         reg_dt.__dict__[rsname], 
                                         reg_dt.__dict__[rdname])
            elif ins.smode in {'@Rn', '@Rn+'}:
                rname = smt_rsrc(fields)
                return time_fn_rsrc(state, inst_dt.__dict__[iname], reg_dt.__dict__[rname])
            else:
                rname = smt_rdst(fields)
                return time_fn_rdst(state, inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        elif ins.name in {'PUSH', 'CALL'} and ins.smode in {'X(Rn)'}:
            rname = smt_rsrc(fields)
            return time_fn_rsrc(state, inst_dt.__dict__[iname], reg_dt.__dict__[rname])
        else:
            return time_fn_noreg(state, inst_dt.__dict__[iname])

    def state_fn(ins, fields, state):
        iname = smt_iname(ins)
        return state_fn_default(state, inst_dt.__dict__[iname])

    z3_data = (time_fn, state_fn, state_fn_init, 
               [time_fn_noreg, time_fn_rsrc, time_fn_rdst, time_fn_rsrc_rdst, state_fn_default, state_fn_init])
    success, solver = do_round_cx(blocks, mk_add_constraint_individual_state, z3_data, cx_max)
    if not success:
        do_round_instr_subset(blocks, mk_add_constraint_instr_state, z3_data, ipreds)
    else:
        create_model_table_7(solver, z3_data, 'NEW_model.pickle')

def split_function_string(fstr):
    lines = fstr.strip().strip('[]').split('\n')
    cases = []
    for line in lines:
        (args, result) = line.split('->')
        args = args.strip().strip('()')
        arg = tuple(a.strip() for a in args.split(','))
        res = result.strip().strip(',')
        cases.append((arg, res))
    return cases

def classify_instr_7():
    i_noreg = []
    i_rsrc = []
    i_rdst = []
    i_rsrc_rdst = []
    for ins in isa.ids_ins:
        iname = smt_iname(ins)
        if ins.fmt in {'fmt1'} and (ins.smode in {'@Rn', '@Rn+'} or ins.dmode in {'Rn'}):
            if   ins.smode in {'@Rn', '@Rn+'} and ins.dmode in {'Rn'}:
                i_rsrc_rdst.append(iname)
            elif ins.smode in {'@Rn', '@Rn+'}:
                i_rsrc.append(iname)
            else:
                i_rdst.append(iname)
        elif ins.name in {'PUSH', 'CALL'} and ins.smode in {'X(Rn)'}:
            i_rsrc.append(iname)
        else:
            i_noreg.append(iname)
    return i_noreg, i_rsrc, i_rdst, i_rsrc_rdst

def get_state_id_7(statestr):
    return int(statestr.split('_')[-1].strip())

def create_model_table_7(solver, z3_data, pname):
    (time_fn, state_fn, state_fn_init, 
     [time_fn_noreg, 
      time_fn_rsrc, 
      time_fn_rdst, 
      time_fn_rsrc_rdst, 
      state_fn_default, 
      state_fn_init],) = z3_data
    
    model = solver.model()
    noreg_strings = str(model[time_fn_noreg])
    rsrc_strings = str(model[time_fn_rsrc])
    rdst_strings = str(model[time_fn_rdst])
    rsrc_rdst_strings = str(model[time_fn_rsrc_rdst])
    state0_strings = str(model[state_fn_init])
    state_strings = str(model[state_fn_default])

    inames = {smt_iname(ins) : ins for ins in isa.ids_ins}
    i_noreg, i_rsrc, i_rdst, i_rsrc_rdst = classify_instr_7()
    states = [0, 1]
    state_default = get_state_id_7(state0_strings)

    noreg_pool = set([(s, x) for s in states for x in i_noreg])
    rsrc_pool = set([(s, x, r) for s in states for x in i_rsrc for r in smt_rnames.values()])
    rdst_pool = set([(s, x, r) for s in states for x in i_rdst for r in smt_rnames.values()])
    rsrc_rdst_pool = set([(s, x, rs, rd) 
                          for s in states 
                          for x in i_rsrc_rdst 
                          for rs in smt_rnames.values() 
                          for rd in smt_rnames.values()])

    # build the timing table

    ttab = {}

    noreg_else = None
    for arg, res in split_function_string(noreg_strings):
        if arg == ('else',):
            noreg_else = int(res)
        else:
            (statestr, iname) = arg
            state = get_state_id_7(statestr)
            if (state, iname) in noreg_pool:
                noreg_pool.remove((state, iname))
                ttab[(state, iname, None, None)] = int(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname))))
    print('noreg_pool has {:d} remaining entries'.format(len(noreg_pool)))
    dadds = 0
    sdefs = 0
    for state, iname in noreg_pool:
        if 'DADD' in iname:
            dadds += 1
            ttab[(state, iname, None, None)] = None
        elif (state_default, iname, None, None) in ttab:
            sdefs += 1
            ttab[(state, iname, None, None)] = ttab[(state_default, iname, None, None)]
        else:
            ins = inames[iname]
            if ins.name in {'RETI'} and ins.smode not in {'Rn'}:
                print('invalid: {:d} {:s}'.format(state, iname))
                ttab[(state, iname, None, None)] = None
            elif ins.name in {'CALL'} and ins.smode in {'#1'}:
                print('invalid: {:d} {:s}'.format(state, iname))
                ttab[(state, iname, None, None)] = None
            elif ins.name in {'RRC', 'SWPB', 'RRA', 'SXT'} and ins.smode in {'#1', '#@N', '#N'}:
                print('invalid: {:d} {:s}'.format(state, iname))
                ttab[(state, iname, None, None)] = None
            else:
                print('using else {:d} for {:s}'.format(noreg_else, repr((state, iname))))
                ttab[(state, iname, None, None)] = noreg_else
    print('excluded {:d} dadds, inferred {:d} behaviors from default state'.format(dadds, sdefs))

    rsrc_else = None
    for arg, res in split_function_string(rsrc_strings):
        if arg == ('else',):
            rsrc_else = int(res)
        else:
            (statestr, iname, rname) = arg
            state = get_state_id_7(statestr)
            if (state, iname, rname) in rsrc_pool:
                rsrc_pool.remove((state, iname, rname))
                ttab[(state, iname, rname, None)] = int(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname, rname))))
    print('rsrc_pool has {:d} remaining entries'.format(len(rsrc_pool)))
    dadds = 0
    sdefs = 0
    invmode = 0
    rnone = 0
    for state, iname, rname in rsrc_pool:
        if 'DADD' in iname:
            dadds += 1
            ttab[(state, iname, rname, None)] = None
        elif (state_default, iname, rname, None) in ttab:
            sdefs += 1
            ttab[(state, iname, rname, None)] = ttab[(state_default, iname, rname, None)]
        elif rname == smt_rnames[-1]:
            rnone += 1
            ttab[(state, iname, rname, None)] = None
        else:
            ins = inames[iname]
            if ins.smode in {'@Rn', '@Rn+'} and rname in {smt_rnames[0]}:
                invmode += 1
                ttab[(state, iname, rname, None)] = None
            elif ins.smode in {'X(Rn)'} and rname in {smt_rnames[0], smt_rnames[2], smt_rnames[3]}:
                invmode += 1
                ttab[(state, iname, rname, None)] = None
            else:
                print('using else {:d} for {:s}'.format(rsrc_else, repr((state, iname, rname))))
                ttab[(state, iname, rname, None)] = rsrc_else
    print('excluded {:d} dadds, {:d} invmode, {:d} rnone, inferred {:d} behaviors from default state'
          .format(dadds, invmode, rnone, sdefs))

    rdst_else = None
    for arg, res in split_function_string(rdst_strings):
        if arg == ('else',):
            rdst_else = int(res)
        else:
            (statestr, iname, rname) = arg
            state = get_state_id_7(statestr)
            if (state, iname, rname) in rdst_pool:
                rdst_pool.remove((state, iname, rname))
                ttab[(state, iname, None, rname)] = int(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname, rname))))
    print('rdst_pool has {:d} remaining entries'.format(len(rdst_pool)))
    dadds = 0
    sdefs = 0
    invmode = 0
    rnone = 0
    for state, iname, rname in rdst_pool:
        if 'DADD' in iname:
            dadds += 1
            ttab[(state, iname, None, rname)] = None
        elif (state_default, iname, None, rname) in ttab:
            sdefs += 1
            ttab[(state, iname, None, rname)] = ttab[(state_default, iname, None, rname)]
        elif rname == smt_rnames[-1]:
            rnone += 1
            ttab[(state, iname, None, rname)] = None
        else:
            ins = inames[iname]
            if ins.smode in {'#1'} and rname in {smt_rnames[0], smt_rnames[2]}:
                invmode += 1
                ttab[(state, iname, None, rname)] = None
            else:
                print('using else {:d} for {:s}'.format(rdst_else, repr((state, iname, rname))))
                ttab[(state, iname, None, rname)] = rdst_else
    print('excluded {:d} dadds, {:d} invmode, {:d} rnone, inferred {:d} behaviors from default state'
          .format(dadds, invmode, rnone, sdefs))


    rsrc_rdst_else = None
    for arg, res in split_function_string(rsrc_rdst_strings):
        if arg == ('else',):
            rsrc_rdst_else = int(res)
        else:
            (statestr, iname, rsname, rdname) = arg
            state = get_state_id_7(statestr)
            if (state, iname, rsname, rdname) in rsrc_rdst_pool:
                rsrc_rdst_pool.remove((state, iname, rsname, rdname))
                ttab[(state, iname, rsname, rdname)] = int(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname, rsname, rdname))))
    print('rsrc_rdst_pool has {:d} remaining entries'.format(len(rsrc_rdst_pool)))
    dadds = 0
    sdefs = 0
    invmode = 0
    rnone = 0
    for state, iname, rsname, rdname in rsrc_rdst_pool:
        if 'DADD' in iname:
            dadds += 1
            ttab[(state, iname, rsname, rdname)] = None
        elif (state_default, iname, rsname, rdname) in ttab:
            sdefs += 1
            ttab[(state, iname, rsname, rdname)] = ttab[(state_default, iname, rsname, rdname)]
        elif rsname == smt_rnames[-1] or rdname == smt_rnames[-1]:
            rnone += 1
            ttab[(state, iname, rsname, rdname)] = None
        else:
            ins = inames[iname]
            if ins.smode in {'@Rn', '@Rn+'} and rsname in {smt_rnames[0]}:
                invmode += 1
                ttab[(state, iname, rsname, rdname)] = None
            elif ins.smode in {'X(Rn)'} and rsname in {smt_rnames[0], smt_rnames[2], smt_rnames[3]}:
                invmode += 1
                ttab[(state, iname, rsname, rdname)] = None
            elif ((ins.smode in {'#1'} or (ins.smode in {'@Rn', '@Rn+'} and rsname in {smt_rnames[2], smt_rnames[3]}))
                  and rdname in {smt_rnames[0], smt_rnames[2]}):
                invmode += 1
                ttab[(state, iname, rsname, rdname)] = None
            else:
                print('using else {:d} for {:s}'.format(rsrc_rdst_else, repr((state, iname, rsname, rdname))))
                ttab[(state, iname, rsname, rdname)] = rsrc_rdst_else
    print('excluded {:d} dadds, {:d} invmode, {:d} rnone, inferred {:d} behaviors from default state'
          .format(dadds, invmode, rnone, sdefs))
    
    # now do the state transitions

    state_pool = set([(s, smt_iname(ins)) for s in states for ins in isa.ids_ins])
    stab = {}
    
    state_else = None

    state_else = None
    for arg, res in split_function_string(state_strings):
        if arg == ('else',):
            state_else = get_state_id_7(res)
        else:
            (statestr, iname) = arg
            state = get_state_id_7(statestr)
            if (state, iname) in state_pool:
                state_pool.remove((state, iname))
                stab[(state, iname)] = get_state_id_7(res)
            else:
                print('not in pool: {:s}'.format(repr((state, iname))))
    print('state_pool has {:d} remaining entries'.format(len(state_pool)))
    for state, iname in state_pool:
        stab[(state, iname)] = state_default
    print('inferred all remaining transitions to default state.')

    print(len(ttab))
    print(len(stab))

    with open(pname, 'wb') as f:
        pickle.dump({'state_default':state_default, 'ttab':ttab, 'stab':stab}, f)

if __name__ == '__main__':
    import sys

    with open(sys.argv[1], 'rb') as f:
        obj = pickle.load(f)

    state_default = obj['state_default']
    ttab = obj['ttab']
    stab = obj['stab']

    inames = {smt_iname(ins) : ins for ins in isa.ids_ins}

    print('timing table (invalid entries are not listed)')
    
    for iname in sorted(inames.keys()):
        if (0, iname, None, None) in ttab:
            v = str(ttab[(0, iname, None, None)])
            if v != 'None':
                print('{:17s} | {:s}'.format(iname, v))
                v1 = str(ttab[(1, iname, None, None)])
                if v != v1:
                    print('                1 | {:s}'.format(v1))

        s = ''
        for rname in smt_rnames.values():
            if (0, iname, rname, None) in ttab:
                v = str(ttab[(0, iname, rname, None)])
                if v == 'None':
                    continue
                s += ('      {:5s} {:5s} | {:s}\n'.format(rname, 'xxxxx', v))
                v1 = str(ttab[(1, iname, rname, None)])
                if v != v1:
                    s += ('    1 {:5s} {:5s} | {:s}\n'.format(rname, 'xxxxx', v1))
        if len(s) > 0:
            print('{:17s} | {:s}'.format(iname, ''))
            print(s, end='')

        s = ''
        for rname in smt_rnames.values():
            if (0, iname, None, rname) in ttab:
                v = str(ttab[(0, iname, None, rname)])
                if v == 'None':
                    continue
                s += ('      {:5s} {:5s} | {:s}\n'.format('xxxxx', rname, v))
                v1 = str(ttab[(1, iname, None, rname)])
                if v != v1:
                    s += ('    1 {:5s} {:5s} | {:s}\n'.format('xxxxx', rname, v1))
        if len(s) > 0:
            print('{:17s} | {:s}'.format(iname, ''))
            print(s, end='')

        s = ''
        for rsname in smt_rnames.values():
            for rdname in smt_rnames.values():
                if (0, iname, rsname, rdname) in ttab:
                    v = str(ttab[(0, iname, rsname, rdname)])
                    if v == 'None':
                        continue
                    s += ('      {:5s} {:5s} | {:s}\n'.format(rsname, rdname, v))
                    v1 = str(ttab[(1, iname, rsname, rdname)])
                    if v != v1:
                        s += ('      {:5s} {:5s} | {:s}\n'.format(rsname, rdname, v1))
        if len(s) > 0:
            print('{:17s} | {:s}'.format(iname, ''))
            print(s, end='')

    print('\nstate transitions: (unlisted transitions are to state 0)')

    for iname in sorted(inames.keys()):
        t0 = stab[(0, iname)]
        t1 = stab[(1, iname)]

        if t0 == 1 or t1 == 1:
            print('{:17s} : 0 -> {:d}'.format(iname, t0))
            print('                    1 -> {:d}'.format(t1))

    # print('DO NOT INVOKE ME')
    # exit(0)

    # Instruction = z3.Datatype('Instruction')
    # Instruction.declare('MOV')
    # Instruction.declare('ADD')
    # Instruction.declare('SUB')
    # Inst = Instruction.create()
    
    # I2 = create_instr_datatype()
    # print(I2)

    # time_instr = z3.Function('time_instr', Inst, z3.IntSort())

    # p1, p2, p3 = z3.Bools('p1 p2 p3')
    # x, y       = z3.Ints('x y')
    # s          = z3.Solver()
    # s.add(z3.Implies(p1, time_instr(Inst.__dict__['MOV']) > 0))
    # s.add(z3.Implies(p2, time_instr(Inst.MOV) == 3))
    # s.add(z3.Implies(p2, y < 1))
    # s.add(z3.Implies(p3, y > -3))
    # s.check(p1, p2, p3)
    # core = s.unsat_core()
    # print(repr(core))
    # print(s.model())
