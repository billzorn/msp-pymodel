#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

import sys
import os
import json
import traceback

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import utils
import msp_fr5969_model as model
from mspdebug_driver import MSPdebug
from msp_emulator import Emulator
from msp_cosim import Cosim
from msp_isa import isa
import cosim as cosim_repl

def is_timer_read(fields, rdst):
    return fields['words'] == [0x4210 | rdst, 0x0350]

def is_reg_store(fields, rsrc):
    words = fields['words']
    if len(words) != 2 or words[0] != 0x40c2 | rsrc << 8:
        return -1
    return words[1]

def is_reg_sub(fields, rsrc, rdst):
    return fields['words'] == [0x8000 | rsrc << 8 | rdst]


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


run_max_steps = 10000
run_interval = 1
run_passes = 3

def check_elf(elfname):
    mulator = Emulator(verbosity=0, tracing=False)
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
            return True

    return False

def trace_elf(elfname, jname):
    with MSPdebug(verbosity=0) as driver:
        mulator = Emulator(verbosity=0, tracing=True)
        mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
        cosim = Cosim([driver, mulator], [True, False], mmap)
        master_idx = 0

        cosim_repl.prog_and_sync(cosim, master_idx, elfname)
        cosim.run(max_steps=run_max_steps, interval=run_interval, passes=run_passes)
        
        diff = cosim.diff()
        trace = mulator.trace
        iotrace = mulator.iotrace2

    with open(jname, 'wt') as f:
        json.dump({'diff':diff, 'trace':trace, 'iotrace':iotrace}, f)

def load_trace(jname):
    with open(jname, 'rt') as f:
        jobj = json.load(f)
    return jobj['diff'], jobj['trace'], jobj['iotrace']

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

def walk_micros(testdir, check, execute, suffix = '.elf',):
    roots = set()
    for root, dirs, files in os.walk(testdir, followlinks=True):
        if root in roots:
            del dirs[:]
            continue
        else:
            roots.add(root)

        for fname in files:
            if fname.endswith(suffix):
                name = fname[:-len(suffix)]
                elfpath = os.path.join(root, fname)
                jpath = os.path.join(root, name + '.json')
                if check:
                    if not check_elf(elfpath):
                        print('Unexpected behavior! {:s}'.format(elfpath))
                        continue
                if execute:
                    try:
                        trace_elf(elfpath, jpath)
                    except Exception:
                        traceback.print_exc()

def walk_traces(testdir):
    blocks = []
    roots = set()
    for root, dirs, files in os.walk(testdir, followlinks=True):
        if root in roots:
            del dirs[:]
            continue
        else:
            roots.add(root)

        for fname in files:
            if fname.endswith('.json'):
                jname = os.path.join(root, fname)
                diff, trace, iotrace = load_trace(jname)
                mismatches = compute_mismatches(diff)
                mismatches_to_blocks(trace, mismatches, blocks)

    return blocks

def main(args):
    testdir = args.testdir
    suffix = args.suffix
    check = args.check
    execute = args.execute
    arffname = args.arff

    if check or execute:
        walk_micros(testdir, check, execute, suffix=suffix)

    if arffname:
        blocks = walk_traces(testdir)
        create_arff(blocks, arffname)

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
    parser.add_argument('-a', '--arff',
                        help='accumulate data into arff file')
    args = parser.parse_args()

    main(args)
    exit(0)




    if len(sys.argv) < 3:
        print('usage: {:s} <ELF> <ARFF>'.format(sys.argv[0]))
        exit(1)

    fname = sys.argv[1]
    arffname = sys.argv[2]

    jname = 'foobar.json'

    trace_elf(fname, jname)
    diff, trace, iotrace = load_trace(jname)
    mismatches = compute_mismatches(diff)
    blocks = []
    mismatches_to_blocks(trace, mismatches, blocks)
    create_arff(blocks, arffname)

    exit(0)
