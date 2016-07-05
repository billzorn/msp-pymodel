# smt bindings through z3

import z3

import utils
from msp_isa import isa

def solve(f):
    formula = z3.parse_smt2_string(f)
    s = z3.Solver()
    s.add(formula)
    print(s.check())
    print(s.unsat_core())

def smt_iname(ins):
    smode_ident = utils.mode_ident[ins.smode]
    dmode_ident = utils.mode_ident[ins.dmode]
    return '_'.join((ins.fmt, ins.name, smode_ident, dmode_ident))

def create_instr_datatype():
    Instruction = z3.Datatype('msp430_Instruction')
    for ins in isa.ids_ins:
        # limit to fmt1 for now
        if ins.fmt != 'fmt1':
            continue
        Instruction.declare(smt_iname(ins))
    #print(Instruction.constructors)
    return Instruction.create()

def create_time_function_0(inst_dt):
    time_instr = z3.Function('time_0', inst_dt, z3.IntSort())
    return time_instr

def add_constraint_0(ident, solver, time_fn, inst_dt, block, cycles):
    p = z3.Bool(ident)
    times = []
    for fields in block:
        ins = isa.decode(fields['words'][0])
        iname = smt_iname(ins)
        times.append(time_fn(inst_dt.__dict__[iname]))
    solver.add(z3.Implies(p, z3.Sum(times) == cycles))
    return p

def solve_0(blocks):
    inst_dt = create_instr_datatype()
    time_fn = create_time_function_0(inst_dt)
    s = z3.Solver()

    i = 0
    predicates = []
    block_preds = {}
    for addr, block, difference in blocks:
        ident = 't_{:d}_{:05x}'.format(i, addr)
        assert len(difference) == 2 and difference[1] == 0
        cycles = difference[0]
        p = add_constraint_0(ident, s, time_fn, inst_dt, block, cycles)
        i += 1
        predicates.append(p)
        block_preds[p] = ident, addr, block, cycles

    core_insns = set()
    core_smodes = set()
    core_dmodes = set()
    core_names = set()
    while s.check(*predicates) == z3.unsat:
        core = s.unsat_core()
        print('-----------------------------')
        print(core)
        print('')
        for pred in core:
            ident, addr, block, cycles = block_preds[pred]
            print(ident)
            for fields in block:
                ins = isa.decode(fields['words'][0])
                fmt, name, smode, dmode = isa.instr_to_modes(ins)
                core_insns.add(ins)

                if fmt == 'fmt1':
                    rsrc = fields['rsrc']
                    rdst = fields['rdst']

                    # hack to avoid some cases common to most tests
                    if not ((smode == '&ADDR' and rdst == 14) or
                            (smode == '#N' and dmode == 'Rn')):
                        core_smodes.add(smode)
                        core_dmodes.add(dmode)
                        core_names.add(name)

                    if 'isrc' in fields:
                        sval = ', {:#x}'.format(fields['isrc'])
                    else:
                        sval = ''
                    print('{:s}\t{:s} (R{:d}{:s}), {:s} (R{:d})'
                          .format(name, smode, rsrc, sval, dmode, rdst))
                else:
                    print('fmt, name, smode, dmode')
                    utils.print_dict(fields)
            print('{:d} total cycles'.format(cycles))
            print('')
            predicates.remove(pred)

    print('=============')
    print('{:d} instructions found in unsat cores'.format(len(core_insns)))
    for ins in core_insns:
        ins.describe()
    print('')
    print('by name:')
    for name in core_names:
        print('  ' + name)
    print('by smode:')
    for smode in core_smodes:
        print('  ' + smode)
    print('by dmode:')
    for dmode in core_dmodes:
        print('  ' + dmode)

def create_ipreds():
    ipreds = {}
    for ins in isa.ids_ins:
        if ins.fmt != 'fmt1':
            continue
        ipreds[ins] = z3.Bool('p_' + smt_iname(ins))
    return ipreds

def add_instr_constraint_0(ipreds, blacklist, solver, time_fn, inst_dt, block, cycles):
    times = []
    insns = set()
    for fields in block:
        ins = isa.decode(fields['words'][0])
        iname = smt_iname(ins)
        times.append(time_fn(inst_dt.__dict__[iname]))
        insns.add(ins)

    preds = [ipreds[ins] for ins in insns if ins not in blacklist]
    solver.add(z3.Implies(z3.And(*preds), z3.Sum(times) == cycles))
    return preds # probably not needed

def solve_instr_0(blocks):
    ipreds = create_ipreds()
    inst_dt = create_instr_datatype()
    time_fn = create_time_function_0(inst_dt)
    s = z3.Solver()
    predicates = list(ipreds.values())

    # filter out instructions we know are common to all traces
    mov_abs_rn = isa.modes_to_instr('fmt1', 'MOV', '&ADDR', 'Rn')
    mov_imm_rn = isa.modes_to_instr('fmt1', 'MOV', '#N', 'Rn')
    blacklist = [mov_abs_rn, mov_imm_rn]

    for addr, block, difference in blocks:
        assert len(difference) == 2 and difference[1] == 0
        cycles = difference[0]
        add_instr_constraint_0(ipreds, blacklist, s, time_fn, inst_dt, block, cycles)

    # should probably look at subsets, but all of these cores are single instruction for fmt1
    while s.check(*predicates) == z3.unsat:
        core = s.unsat_core()
        print(core)
        for pred in core:
            predicates.remove(pred)

    # m = s.model()
    # for d in m:
    #     print(d, m[d])


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

def create_time_function_1(inst_dt, reg_dt):
    time_instr = z3.Function('time_1', inst_dt, reg_dt, z3.IntSort())
    return time_instr

def add_constraint_1(ident, solver, time_fn, inst_dt, reg_dt, block, cycles):
    p = z3.Bool(ident)
    times = []
    for fields in block:
        ins = isa.decode(fields['words'][0])
        iname = smt_iname(ins)
        rname = smt_rsrc(fields)
        times.append(time_fn(inst_dt.__dict__[iname], reg_dt.__dict__[rname]))
    solver.add(z3.Implies(p, z3.Sum(times) == cycles))
    return p

def solve_1(blocks):
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()
    time_fn = create_time_function_1(inst_dt, reg_dt)
    s = z3.Solver()

    i = 0
    predicates = []
    for addr, block, difference in blocks:
        ident = 't_{:d}_{:05x}'.format(i, addr)
        assert len(difference) == 2 and difference[1] == 0
        cycles = difference[0]
        p = add_constraint_1(ident, s, time_fn, inst_dt, reg_dt, block, cycles)
        i += 1
        predicates.append(p)

    print(s.check(*predicates))

    generated_fn = s.model()[time_fn]
    z3.set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)
    print(generated_fn)

def add_constraint_1_0(ident, solver, time_macro, inst_dt, reg_dt, block, cycles):
    p = z3.Bool(ident)
    times = []
    for fields in block:
        ins = isa.decode(fields['words'][0])
        iname = smt_iname(ins)
        rname = smt_rsrc(fields)
        times.append(time_macro(ins.smode, inst_dt.__dict__[iname], reg_dt.__dict__[rname]))
    solver.add(z3.Implies(p, z3.Sum(times) == cycles))
    return p

def solve_1_0(blocks):
    inst_dt = create_instr_datatype()
    reg_dt = create_reg_datatype()
    time_fn_0 = create_time_function_0(inst_dt)
    time_fn_1 = create_time_function_1(inst_dt, reg_dt)
    s = z3.Solver()

    def time_macro(smode, inst_obj, reg_obj):
        if smode in ['@Rn', '@Rn+']:
            return time_fn_1(inst_obj, reg_obj)
        else:
            return time_fn_0(inst_obj)

    i = 0
    predicates = []
    for addr, block, difference in blocks:
        ident = 't_{:d}_{:05x}'.format(i, addr)
        assert len(difference) == 2 and difference[1] == 0
        cycles = difference[0]
        p = add_constraint_1_0(ident, s, time_macro, inst_dt, reg_dt, block, cycles)
        i += 1
        predicates.append(p)

    print(s.check(*predicates))

    generated_fn = s.model()[time_fn_0]
    z3.set_option(max_args=10000000, max_lines=1000000, max_depth=10000000, max_visited=1000000)
    print(generated_fn)
    generated_fn = s.model()[time_fn_1]
    print(generated_fn)


if __name__ == '__main__':
    Instruction = z3.Datatype('Instruction')
    Instruction.declare('MOV')
    Instruction.declare('ADD')
    Instruction.declare('SUB')
    Inst = Instruction.create()
    
    I2 = create_instr_datatype()
    print(I2)

    time_instr = z3.Function('time_instr', Inst, z3.IntSort())

    p1, p2, p3 = z3.Bools('p1 p2 p3')
    x, y       = z3.Ints('x y')
    s          = z3.Solver()
    s.add(z3.Implies(p1, time_instr(Inst.__dict__['MOV']) > 0))
    s.add(z3.Implies(p2, time_instr(Inst.MOV) == 3))
    s.add(z3.Implies(p2, y < 1))
    s.add(z3.Implies(p3, y > -3))
    s.check(p1, p2, p3)
    core = s.unsat_core()
    print(repr(core))
    print(s.model())

    # observations / TODO

    # we've sorted out some examples of unsat cores that indiciate that the timing behavior is
    # different when using the constant generator. This is expected

    # I have no idea what's going on with the other unsat cores that involve 4 traces.
    # Further investigation is required.
    # Upon further investigation, we have the same situation where the different timing
    # of CG modes causes the core, but since we have different numbers of MOV instructions
    # in the conflicting traces, we need some more traces to "lock" the behavior of the
    # setup MOV instructions so that we can't just change those timings to fix the conflicting
    # pair.

    # WIP figuring out if this is actually the best way to get counterexamples, or if we could
    # do something different.
    # Idea: one predicate per instruction. Question is, what do we do to the predicates once
    # we see the first unsat core (which is trivial, the measurement move instr is in
    # every single trace).
    # This should be working now.

    # WIP figuring out what to do with the partial functions we end up generating. I think
    # the best thing to do is split on some condition in a wrapper function, and invoke
    # either a simpler function with less context if we can or a more complex one if we
    # need to. The split is done manually, but both functions can be learned simultaneously.
    # I'm not sure if this is the right thing to do, or if we can do something more clever.

    # Z3 only wants to tell me about my predicates in the model, not the actual timing function.
    # this is super annoying. Might need to go to a push/pop style with named assertions, or
    # set up a different solver once we think we know the right subset of instructions.

    # Z3 bindings are flaky, installation is not obvious and possibly incorrect right now. Meh.
    # I hope it is working correctly incrementally. Performance not a huge issue, but we'll see
    # what happens when we have millions of traces.
