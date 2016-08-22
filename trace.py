#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

import sys
import os
import json
import codecs
import traceback
import multiprocessing

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import utils
import msp_fr5969_model as model
from mspdebug_driver import MSPdebug
from msp_emulator import Emulator
from msp_cosim import Cosim
from msp_isa import isa
import cosim as cosim_repl
import smt

def is_timer_read(fields, rdst):
    return fields['words'] == [0x4210 | rdst, 0x0350]

def is_reg_store(fields, rsrc):
    words = fields['words']
    if len(words) != 2 or words[0] != 0x40c2 | rsrc << 8:
        return -1
    return words[1]

def is_reg_sub(fields, rsrc, rdst):
    return fields['words'] == [0x8000 | rsrc << 8 | rdst]

run_max_steps = 10000
run_interval = 1
run_passes = 3

def check_elf(elfname, verbosity = 0):
    mulator = Emulator(verbosity=verbosity, tracing=True)
    mulator.prog(elfname)

    fram_end = mulator.md(model.upper_start - 256, 256)
    for byte in fram_end[:-2]:
        if byte != 255:
            print('Invalid prog write to reserved fram region:')
            print(utils.triple_summarize(fram_end, model.upper_start - 256))
            return False

    for i in range(run_passes):
        success, steps = mulator.run(run_max_steps)
        if not success:
            return False
        elif steps < run_max_steps:
            fram_end = mulator.md(model.upper_start - 256, 256)
            for byte in fram_end[:-2]:
                if byte != 255:
                    print('Invalid run write to reserved fram region:')
                    print(utils.triple_summarize(fram_end, model.upper_start - 256))
                    return False
            if verbosity >= 0:
                print('  checked {:s}, pass'.format(elfname))
            return True

    return False

def trace_elf(elfname, jname, verbosity = 0):
    with MSPdebug(verbosity=verbosity) as driver:
        mulator = Emulator(verbosity=verbosity, tracing=True)
        mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
        cosim = Cosim([driver, mulator], [True, False], mmap)
        master_idx = 0

        cosim_repl.prog_and_sync(cosim, master_idx, elfname)
        cosim.run(max_steps=run_max_steps, interval=run_interval, passes=run_passes)

        diff = cosim.diff()
        trace = mulator.trace
        iotrace = mulator.iotrace2

    with utils.Write7z(jname) as f:
        writer = codecs.getwriter('utf-8')
        json.dump({'diff':diff, 'trace':trace, 'iotrace':iotrace}, writer(f))

    if verbosity >= 0:
        print('  traced {:s} to {:s}'.format(elfname, jname))

def load_trace(jname):
    with utils.Read7z(jname) as f:
        reader = codecs.getreader('utf-8')
        jobj = json.load(reader(f))
    return jobj['diff'], jobj['trace'], jobj['iotrace']

trace_suffix = '.trace.json.7z'

def compute_mismatches(diff):
    mismatches = {}
    for addr in diff:
        if addr != 'regs':
            mems = diff[addr]
            assert len(mems) == 2
            assert len(mems[0]) == len(mems[1])
            for i in range(len(mems[0])):
                if mems[0][i] != mems[1][i]:
                    mismatches[int(addr)+i] = (mems[0][i], mems[1][i])
    return mismatches

# Consumes mismatches to add to blocks.
# Asserts that mismatches is empty when it finishes (no mismatches were not able
# to be explained by looking at the trace).
def mismatches_to_blocks(trace, mismatches, blocks):
    current = []
    in_region = False
    in_store = False
    for fields in trace:
        if is_timer_read(fields, 14):
            assert current == [] and in_region == False
            in_region = True
        elif is_timer_read(fields, 15):
            assert len(current) > 0 and in_region == True
            in_region = False
        elif is_reg_sub(fields, 14, 15):
            assert in_region == False
            in_store = True

        if in_store:
            assert in_region == False
            addr = is_reg_store(fields, 15)
            if addr > 0:
                # print('{:s} | {:s}'.format(repr(addr), repr(current)))
                blocks.append((addr, current, mismatches.pop(addr)))
                current = []
                in_store = False

        elif in_region:
            current.append(fields)

def arff_header():
    s = "@relation 'cycle_count'\n"
    for i, ins in enumerate(isa.ids_ins):
        s += '@attribute {:s} numeric\n'.format('_'.join(isa.idx_to_modes(i)))
    return s + '@attribute cycles numeric\n@data'

def arff_entry(indices, cycles):
    bins = {}
    for k in indices:
        bins[k] = bins.setdefault(k, 0) + 1
    return ', '.join([str(bins[i]) if i in bins else '0' for i in range(len(isa.ids_ins))] + [str(cycles)])

def create_arff(blocks, arffname):
    with open(arffname, 'wt') as f:
        f.write(arff_header() + '\n')

        for addr, block, difference in blocks:
            assert(len(difference) == 2 and difference[1] == 0)
            cycles = difference[0]
            indices = []
            description = []
            for fields in block:
                ins = isa.decode(fields['words'][0])
                idx = isa.instr_to_idx(ins)
                modes = isa.idx_to_modes(idx)
                indices.append(idx)
                description.append('  {:s} {:s}, {:s}'.format(*modes[1:]))

            f.write(arff_entry(indices, cycles) + '\n')

def create_json(blocks, jname):
    with open(jname, 'wt') as f:
        json.dump({'blocks':blocks}, f)

def extract_json(jname):
    with open(jname, 'rt') as f:
        jobj = json.load(f)
    return jobj['blocks']

def walk_par(fn, targetdir, cargs, n_procs = 1, verbosity = 0):
    roots = set()
    worklists = [(i, [], cargs) for i in range(n_procs)]
    i = 0
    for root, dirs, files in os.walk(targetdir, followlinks=True):
        if root in roots:
            del dirs[:]
            continue
        else:
            roots.add(root)
        for fname in files:
            worklists[i%n_procs][1].append((root, fname))
            i += 1

    if verbosity >= 0:
        if n_procs == 1:
            print('found {:d} files under {:s}, running on main process'
                  .format(i, targetdir))
        else:
            print('found {:d} files under {:s}, splitting across {:d} processes'
                  .format(i, targetdir, n_procs))

    if n_procs == 1:
        return fn(worklists[0])
    else:
        pool = multiprocessing.Pool(processes=n_procs)
        return pool.map(fn, worklists)

def process_micros(args):
    (k, files, (check, execute, suffix, abort_on_error, verbosity)) = args
    i = 0

    for root, fname in files:
        if fname.endswith(suffix):
            i += 1
            name = fname[:-len(suffix)]
            elfpath = os.path.join(root, fname)
            jpath = os.path.join(root, name + trace_suffix)
            if check:
                if not check_elf(elfpath, verbosity=verbosity):
                    print('Unexpected behavior! {:s}'.format(elfpath))
                    if abort_on_error:
                        break
                    else:
                        continue
            if execute:
                assert k == 0, 'microbenchmark execution only supports one process'
                try:
                    trace_elf(elfpath, jpath, verbosity=verbosity)
                except Exception:
                    traceback.print_exc()
                    if abort_on_error:
                        break

    if verbosity >= 0:
        print('processed {:d} microbenchmarks, done'.format(i))
    return i

def walk_micros(testdir, check, execute, suffix = '.elf', abort_on_error = True,
                verbosity = 0, n_procs = 1):
    if execute and n_procs != 1:
        print('Warning: microbenchmark execution only supports one process, using n_procs=1')
        n_procs = 1

    counts = walk_par(process_micros, testdir, (check, execute, suffix, abort_on_error, verbosity),
                      n_procs=n_procs, verbosity=verbosity)

    if n_procs > 1 and verbosity >= 0:
        print('dispatched to {:d} cores, processed {:d} total microbenchmarks'
              .format(n_procs, sum(counts)))

def process_traces(args):
    (k, files, (verbosity,)) = args
    i = 0
    blocks = []

    for root, fname in files:
        if fname.endswith(trace_suffix):
            i += 1
            jname = os.path.join(root, fname)
            diff, trace, iotrace = load_trace(jname)
            mismatches = compute_mismatches(diff)
            mismatches_to_blocks(trace, mismatches, blocks)

    if verbosity >= 0:
        print('processed {:d} traces to {:d} observed blocks, done'.format(i, len(blocks)))
    return i, blocks

def walk_traces(testdir, verbosity = 0, n_procs = 1):
    results = walk_par(process_traces, testdir, (verbosity,),
                       n_procs=n_procs, verbosity=verbosity)

    count = 0
    blocks = []
    for i, subblocks in results:
        count += i
        blocks += subblocks

    if n_procs > 1 and verbosity >= 0:
        print('dispatched to {:d} cores, processed {:d} total traces to {:d} blocks'
              .format(n_procs, count, len(blocks)))
    return blocks

def main(args):
    testdir = args.testdir
    suffix = args.suffix
    check = args.check
    execute = args.execute
    jname = args.json
    arffname = args.arff
    smtround = args.smt
    n_procs = args.ncores
    abort_on_error = not args.noabort
    verbosity = args.verbose

    if check or execute:
        walk_micros(testdir, check, execute, suffix=suffix, abort_on_error=abort_on_error,
                    n_procs=n_procs, verbosity=verbosity)

    if jname or arffname or smtround > 0:
        if jname:
            if os.path.exists(jname):
                blocks = extract_json(jname)
            else:
                blocks = walk_traces(testdir, verbosity=verbosity, n_procs=n_procs)
                create_json(blocks, jname)
        else:
            blocks = walk_traces(testdir, verbosity=verbosity, n_procs=n_procs)

        if arffname:
            create_arff(blocks, arffname)

        if smtround > 0:

            if   smtround == 1:
                smt.round_1(blocks)
            elif smtround == 2:
                smt.round_2(blocks)
            elif smtround == 3:
                smt.round_3(blocks)
            elif smtround == 4:
                smt.round_4(blocks)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('testdir',
                        help='directory to look for files in')
    parser.add_argument('suffix', nargs='?', default='.elf',
                        help='suffix for executable micro files')
    parser.add_argument('-c', '--check', action='store_true',
                        help='check micros for incorrect behavior under emulation')
    parser.add_argument('-e', '--execute', action='store_true',
                        help='execute micros against real hardware')
    parser.add_argument('-j', '--json',
                        help='accumulate constraint blocks into raw json file')
    parser.add_argument('-a', '--arff',
                        help='accumulate data into arff file')
    parser.add_argument('-s', '--smt', type=int, default=0,
                        help='run analysis round with smt solver')
    parser.add_argument('-v', '--verbose', type=int, default=0,
                        help='verbosity level')
    parser.add_argument('-noabort', action='store_true',
                        help='do not abort after first failure')
    parser.add_argument('-ncores', type=int, default=1,
                        help='run in parallel on this many cores')
    args = parser.parse_args()

    main(args)
    exit(0)
