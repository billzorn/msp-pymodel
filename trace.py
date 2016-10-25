#!/usr/bin/env python3

# step through an executable under cosimulation and report errors

#import objgraph

import sys
import os
import json
import codecs
import traceback
import multiprocessing
import pickle

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

run_max_steps = 20000
run_interval = 1
run_passes = 5

def check_elf(elfname, verbosity = 0):
    mulator = Emulator(verbosity=verbosity, tracing=True)
    mulator.prog(elfname)

    fram_end = mulator.md(model.upper_start - 256, 256)
    for byte in fram_end[:-2]:
        if byte != 255:
            print('Invalid prog write to reserved fram region:')
            print(utils.triple_summarize(fram_end, model.upper_start - 256))
            return False
    resetvec = fram_end[-2:]

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
            if fram_end[-2:] != resetvec:
                print('Broke the reset vector?')
                print('was', resetvec)
                print('now', fram_end[-2:])
                return False
            upper = mulator.md(model.upper_start, model.upper_size)
            for byte in upper:
                if byte != 255:
                    print('Modified upper memory?')
                    print(utils.triple_summarize(upper, model.upper_start))
                    return False
            touchdown = mulator.md(mulator.regs()[0], 16)
            expected_touchdown = [0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xff, 0x3f, 0xf8, 0x3f]
            if touchdown != expected_touchdown:
                print('Missed touchdown pad:')
                print('  expecting', expected_touchdown)
                print('  got', touchdown)
                return False
            if verbosity >= 0:
                print('  checked {:s}, pass'.format(elfname))
            return True

    print('Did not complete?')
    return False

def trace_elf(elfname, jname, tty = None, logname = None, verbosity = 0):
    if logname is None:
        with MSPdebug(tty=tty, logf=sys.stdout, verbosity=verbosity) as driver:
            mulator = Emulator(verbosity=verbosity, tracing=True)
            mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
            cosim = Cosim([driver, mulator], [True, False], mmap)
            master_idx = 0

            cosim_repl.prog_and_sync(cosim, master_idx, elfname)
            cosim.run(max_steps=run_max_steps, interval=run_interval, passes=run_passes)

            diff = cosim.diff()
            trace = mulator.trace
            iotrace = mulator.iotrace2
    else:
        with open(logname, 'at') as f:
            with MSPdebug(tty=tty, logf=f, verbosity=max(verbosity,1)) as driver:
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

def retrace_elf(elfname, jname, tinfo, interesting_blocks, verbosity = 0):
    if not os.path.isfile(jname):
        print('skipping {:s}, no trace {:s}'.format(elfname, jname))
        return True

    timulator = Emulator(verbosity=verbosity, tracing=True, tinfo=tinfo)
    mulator = Emulator(verbosity=verbosity, tracing=True)
    mmap = [(model.ram_start, model.ram_size), (model.fram_start, model.fram_size)]
    cosim = Cosim([timulator, mulator], [False, False], mmap)
    master_idx = 0

    cosim_repl.prog_and_sync(cosim, master_idx, elfname)
    cosim.run(max_steps=run_max_steps, interval=run_interval, passes=run_passes)

    tmp_jstr = json.dumps({'diff':cosim.diff(), 'trace':mulator.trace, 'iotrace':mulator.iotrace2})
    tmp_jobj = json.loads(tmp_jstr)

    diff = tmp_jobj['diff']
    trace = tmp_jobj['trace']
    iotrace = tmp_jobj['iotrace']
    old_diff, old_trace, old_iotrace = load_trace(jname)

    same = diff == old_diff
    if verbosity >= 0:
        print('  timed emulated {:s} against {:s}. Same? {:s}'
              .format(elfname, jname, repr(same)))
        # print('---ORIGINAL---')
        # utils.explain_diff(old_diff)
        # print('---EMULATOR---')
        # utils.explain_diff(diff)

    if not same:
        old_blocks = []
        old_mismatches = compute_mismatches(old_diff, verbosity=verbosity)
        old_err = mismatches_to_blocks(old_trace, old_mismatches, old_blocks)
        blocks = []
        mismatches = compute_mismatches(diff, verbosity=verbosity)
        err = mismatches_to_blocks(trace, mismatches, blocks)

        if old_err and err:
            print('    failures in both traces: {:s}'.format(elfname))
        elif old_err:
            print('    BAD: failures in hardware trace: {:s}'.format(elfname))
        elif old_err:
            print('    BAD: failures in emulator trace: {:s}'.format(elfname))
        else:
            print('    successful trace: {:s}'.format(elfname))

        old_blocks_index = {addr: (x, y) for (addr, x, y) in old_blocks}
        trace_errors = 0
        uncovered = 0
        for (addr, block, difference) in blocks:
            if addr in old_blocks_index:
                old_block, old_difference = old_blocks_index.pop(addr)
                if block != old_block:
                    print('      BAD: trace difference at {:05x}'.format(addr))
                    trace_errors += 1
                elif difference != old_difference:
                    interesting_blocks.append((addr, old_block, old_difference))
            else:
                uncovered += 1

        if trace_errors > 0:
            print('    BAD: {:d} trace differences'.format(trace_errors))
        if uncovered > 0 or len(old_blocks_index) > 0:
            print('    BAD: {:d} blocks unique to hardware, {:d} to emulator'
                  .format(len(old_blocks_index), uncovered))

    return same

def load_trace(jname):
    with utils.Read7z(jname) as f:
        reader = codecs.getreader('utf-8')
        jobj = json.load(reader(f))
    return jobj['diff'], jobj['trace'], jobj['iotrace']

trace_suffix = '.trace.json.7z'

def compute_mismatches(diff, verbosity):
    mismatches = {}
    for addr in diff:
        if addr == 'regs':
            if verbosity >= 1:
                print('nonempty reg diff???')
                utils.explain_diff(diff)
        else:
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
    missing = 0
    err = False
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
                if addr in mismatches:
                    blocks.append((addr, current, mismatches.pop(addr)))
                else:
                    # print('MISSING {:s} | {:s}'.format(repr(addr), repr(current)))
                    missing += 1
                    err = True
                current = []
                in_store = False

        elif in_region:
            current.append(fields)

    if err:
        print('Unexpected blocks! {:d} blocks have no corresponding mismatches, {:d} unexplained mismatches in diff.'
              .format(missing, len(mismatches)))

    elif len(mismatches) > 0:
        err = True
        print('State mismatch! {:d} unexplained mismatches in diff.'
              .format(len(mismatches)))
        print(mismatches)

    return err

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
    if jname.endswith('.json.7z'):
        with utils.Read7z(jname) as f:
            reader = codecs.getreader('utf-8')
            jobj = json.load(reader(f))
        return jobj['blocks']
    else:
        with open(jname, 'rt') as f:
            jobj = json.load(f)
        return jobj['blocks']

def walk_par(fn, targetdir, cargs, n_procs = 1, verbosity = 0):
    if os.path.isfile(targetdir):
        if verbosity >= 0:
            print('target is a single file, processing directly')
            return [fn((0, [('', targetdir)], cargs))]

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
        return [fn(worklists[0])]
    else:
        pool = multiprocessing.Pool(processes=n_procs)
        return pool.map(fn, worklists)

def process_micros(args):
    (k, files, (check, execute, tinfo, suffix, abort_on_error, ttys, verbosity)) = args
    i = 0
    retrace_differences = []
    blocks = []

    if verbosity >= 1:
        pid = os.getpid()
        logname = 'pytrace.{:d}.log.txt'.format(pid)
    else:
        logname = None

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
                if ttys is None:
                    assert k == 0, 'specify multiple TTYs to run more than one process'
                    tty = None
                else:
                    assert 0 <= k and k < len(ttys), 'must specify at least one TTY per process'
                    tty = ttys[k]

                # MAKE THIS A REAL OPTION PLS
                max_retries = 3
                retries = 0
                while retries < max_retries:
                    try:
                        trace_elf(elfpath, jpath, tty=tty, logname=logname, verbosity=verbosity)
                        break
                    except Exception:
                        traceback.print_exc()
                        retries += 1

                if abort_on_error and retries >= max_retries:
                    break

            if tinfo:
                same = retrace_elf(elfpath, jpath, tinfo, blocks, verbosity=verbosity)
                if not same:
                    retrace_differences.append(elfpath)

    if verbosity >= 0:
        print('processed {:d} microbenchmarks, done'.format(i))
    return i, retrace_differences, blocks

def walk_micros(testdir, check, execute, tinfo, suffix = '.elf', abort_on_error = True,
                ttys = None, verbosity = 0, n_procs = 1):

    retrace_data = walk_par(process_micros, testdir, 
                                   (check, execute, tinfo, suffix, abort_on_error, ttys, verbosity),
                                   n_procs=n_procs, verbosity=verbosity)

    count = 0
    count_differences = 0
    printed_header = False
    interesting_blocks = []
    for i, differences, blocks in retrace_data:
        count += i
        interesting_blocks += blocks
        for elfpath in differences:
            if not printed_header:
                print('Emulated timing model disagreed for traces:')
                printed_header = True
            print('  {:s}'.format(elfpath))
            count_differences += 1

    if n_procs > 1 and verbosity >= 0:
        print('dispatched to {:d} cores, processed {:d} total microbenchmarks, {:d} timing differences'
              .format(n_procs, count, count_differences))

    if len(interesting_blocks) > 0 and verbosity >= 0:
        print('recovered {:d} interesting blocks that differ in hardware and emulation'
              .format(len(interesting_blocks)))

    return interesting_blocks

def process_traces(args):
    (k, files, (prefix, verbosity)) = args
    i = 0
    errs = 0
    blocks = []

    for root, fname in files:
        if fname.startswith(prefix) and fname.endswith(trace_suffix):
            i += 1
            jname = os.path.join(root, fname)
            diff, trace, iotrace = load_trace(jname)
            mismatches = compute_mismatches(diff, verbosity=verbosity)
            err = mismatches_to_blocks(trace, mismatches, blocks)
            if err:
                print('  failures in trace {:s}'.format(jname))
                errs += 1
            elif verbosity >= 1:
                print('  successful trace {:s}'.format(jname))
            # if verbosity >= 2:
            #     objgraph.show_growth()
            #     print('{:d} blocks total'.format(len(blocks)))
            #     print(utils.recursive_container_count(blocks))

    if verbosity >= 0:
        print('processed {:d} traces to {:d} observed blocks, {:d} failures, done'
              .format(i, len(blocks), errs))
    return i, blocks

def walk_traces(testdir, prefix = '', verbosity = 0, n_procs = 1):
    results = walk_par(process_traces, testdir, (prefix, verbosity),
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
    jin_list = args.jsonin
    jout = args.jsonout
    cjin_list = args.cjsonin
    cjout = args.cjsonout
    arffname = args.arff
    smtround = args.smt
    n_procs = args.ncores
    abort_on_error = not args.noabort
    trprefix = args.trprefix
    tinfo_name = args.timing
    ttys = args.tty
    verbosity = args.verbose

    did_work = False

    if tinfo_name:
        with open(tinfo_name, 'rb') as f:
            tinfo = pickle.load(f)
    else:
        tinfo = None
        
    if check or execute or tinfo:
        did_work = True
        interesting_blocks = walk_micros(testdir, check, execute, tinfo, 
                                         suffix=suffix, abort_on_error=abort_on_error,
                                         n_procs=n_procs, ttys=ttys, verbosity=verbosity)
    else:
        interesting_blocks = None

    if jout or cjout or arffname or smtround > 0:
        did_work = True
        if interesting_blocks is not None:
              blocks = interesting_blocks
        elif jin_list:
            blocks = []
            for jname in jin_list:
                new_blocks = extract_json(jname)
                if verbosity >= 0:
                    print('read {:d} blocks from {:s}'
                          .format(len(new_blocks), jname))
                blocks += new_blocks
        elif not cjin_list:
            blocks = walk_traces(testdir, prefix=trprefix, verbosity=verbosity, n_procs=n_procs)
        else:
            blocks = []

        if cjin_list:
            smt_blocks = []
            for jname in cjin_list:
                new_smt_blocks = extract_json(jname)
                if verbosity >= 0:
                    print('read {:d} smt blocks from {:s}'
                          .format(len(new_smt_blocks), jname))
                smt_blocks += new_smt_blocks
        else:
            smt_blocks = []
            
        if len(blocks) + len(smt_blocks) <= 0:
              print('no blocks found, nothing else to do')
              return

        if jout:
            create_json(blocks, jout)
            if verbosity >= 0:
                print('wrote {:d} blocks to {:s}'.format(len(blocks), jout))

        if arffname:
            create_arff(blocks, arffname)
            if verbosity >= 0:
                print('wrote {:d} blocks to {:s}'.format(len(blocks), arffname))

        if cjout:
            smt_blocks += smt.compress_blocks(blocks)
            blocks = []
            create_json(smt_blocks, cjout)
            if verbosity >= 0:
                print('wrote {:d} smt blocks to {:s}'.format(len(smt_blocks), cjout))

        if smtround > 0:

            # destructive
            smt_blocks += smt.compress_blocks(blocks)

            if   smtround == 1:
                smt.round_1(smt_blocks)
            elif smtround == 2:
                smt_blocks.reverse()
                smt.round_2(smt_blocks)
            elif smtround == 3:
                smt.round_3(smt_blocks)
            elif smtround == 4:
                smt.round_4(smt_blocks)
            elif smtround == 5:
                #smt_blocks.reverse()
                smt.round_5(smt_blocks)
            elif smtround == 6:
                smt.round_6(smt_blocks)
            elif smtround == 7:
                smt.round_7(smt_blocks)
            elif smtround == 8:
                smt.round_8(smt_blocks)
            elif smtround == 9:
                smt.round_9(smt_blocks)
            elif smtround == 10:
                smt.round_10(smt_blocks)


    if not did_work:
        print('Nothing to do.')
        return


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('testdir', nargs='?', default='.',
                        help='directory to look for files in')
    parser.add_argument('suffix', nargs='?', default='.elf',
                        help='suffix for executable micro files')
    parser.add_argument('-c', '--check', action='store_true',
                        help='check micros for incorrect behavior under emulation')
    parser.add_argument('-e', '--execute', action='store_true',
                        help='execute micros against real hardware')
    parser.add_argument('-ji', '--jsonin', nargs='+',
                        help='read constraint blocks from json files')
    parser.add_argument('-jo', '--jsonout',
                        help='accumulate constraint blocks into raw json file')
    parser.add_argument('-cji', '--cjsonin', nargs='+',
                        help='read constraint blocks from smt-compressed json files')
    parser.add_argument('-cjo', '--cjsonout',
                        help='smt compress blocks into json file')
    parser.add_argument('-a', '--arff',
                        help='accumulate data into arff file')
    parser.add_argument('-s', '--smt', type=int, default=0,
                        help='run analysis round with smt solver')
    parser.add_argument('-t', '--timing',
                        help='use this pickled timing model to emulate Timer_A')
    parser.add_argument('-v', '--verbose', type=int, default=0,
                        help='verbosity level')
    parser.add_argument('-noabort', action='store_true',
                        help='do not abort after first failure')
    parser.add_argument('-ncores', type=int, default=1,
                        help='run in parallel on this many cores')
    parser.add_argument('-trprefix', default='',
                        help='only read traces with this prefix')
    parser.add_argument('-tty', default=None, nargs='+',
                        help='connect to mspdebug on these TTYs')


    args = parser.parse_args()

    main(args)
    exit(0)
