#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

import sys
import os
import json

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

def trace_elf(elfname, jname):
    with MSPdebug(verbosity=0) as driver:
        mulator = Emulator(verbosity=0, tracing=True)
        mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
        cosim = Cosim([driver, mulator], [True, False], mmap)
        master_idx = 0

        cosim_repl.prog_and_sync(cosim, master_idx, elfname)

        max_steps = 10000
        interval = 1
        passes = 3
        cosim.run(max_steps=max_steps, interval=interval, passes=passes)
        
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



if __name__ == '__main__':
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
