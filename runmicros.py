#!/usr/bin/env python3

import sys
import os

import random
random.seed(773)

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import msp_micros as micros
import msp_elftools as elftools
import utils
import msp_cfg as cfg


def iter_states_and_write(args):
    (k, gen, (testdir, measure, verbosity)) = args
    i = 0
    metrics = []
    for state in micros.iter_states(gen, measure=measure, verbosity=verbosity, metrics=metrics):
        tname = os.path.join(testdir, 'p{:d}t{:d}.elf'.format(k, i))
        elftools.save(state, tname)
        i += 1
    if verbosity >= 1:
        print('generated {:d} benchmark images'.format(i))
    return i, metrics[0]

def get_seqs_from_image(fname, i, reset_reg = False):
    graph = cfg.CFG(fname, verbosity=1)
    graph.build_graph(do_quadratic_checks=True)
    seqs = graph.get_seqs(i)

    for list_of_seqs in seqs:
        for seq in list_of_seqs:
            free_reg = {4,5,6,7,8,9,10,11,12,13}
            if not reset_reg:
                for ins, fields in seq:
                    if 'rsrc' in fields and fields['rsrc'] in free_reg:
                        free_reg.remove(fields['rsrc'])
                    if 'rdst' in fields and fields['rdst'] in free_reg:
                        free_reg.remove(fields['rdst'])
            microseqs = [[]]
            for ins, fields in seq:
                if (ins.fmt in {'jump'} or 'jump_taken' in fields) and ins.name not in {'JMP'}:
                    new_microseqs = []
                    fields['jump_taken'] = True
                    for microseq in microseqs:
                        microseq.append(micros.micro_description(ins, fields))
                        new_microseqs.append(microseq + [micros.micro_description(ins, fields)])
                    fields['jump_taken'] = False
                    for microseq in microseqs:
                        microseq.append(micros.micro_description(ins, fields))
                        new_microseqs.append(microseq + [micros.micro_description(ins, fields)])
                    microseqs += new_microseqs
                else:
                    if ins.name in {'JMP'}:
                        fields['jump_taken'] = True
                    if 'rsrc' in fields and fields['rsrc'] > 3 and (reset_reg or fields['rsrc'] > 13):
                        if free_reg:
                            fields['rsrc'] = free_reg.pop()
                        else:
                            fields['rsrc'] = random.randint(4,13)
                    if 'rdst' in fields and fields['rdst'] > 3 and (reset_reg or fields['rdst'] > 13):
                        if free_reg:
                            fields['rdst'] = free_reg.pop()
                        else:
                            fields['rdst'] = random.randint(4,13)

                    for microseq in microseqs:
                        microseq.append(micros.micro_description(ins, fields))
            for microseq in microseqs:
                yield microseq

def main(args):
    testdir = args.testdir
    n = args.depth
    measure = args.measure
    fname = args.fname
    reset_reg = args.rr
    verbosity = args.verbose
    ncores = args.ncores

    if fname:
        generator = get_seqs_from_image(fname, n, reset_reg=reset_reg)
    elif args.iterator == 'offset':
        generator = micros.iter_offset(n)
    elif args.iterator == 'rep':
        generator = micros.iter_reps(n)
    else:
        generator = micros.iter_to_depth(n)


    if ncores == 1:
        iter_states_and_write((0, generator, (testdir, measure, verbosity)))
    else:
        metrics = utils.iter_par(iter_states_and_write, generator, (testdir, measure, verbosity), ncores)

        if verbosity >= 1:
            images = 0
            successes_total = 0
            conflicts_total = 0
            condition_total = 0
            other_total = 0
            for i, (successes, conflict_failures, condition_failures, other_failures) in metrics:
                images += i
                successes_total += successes
                conflicts_total += conflict_failures
                condition_total += condition_failures
                other_total += other_failures
            print('dispatched to {:d} cores, generated {:d} total benchmark images'
                  .format(ncores, images))
            print('  {:d} successes, {:d} conflicts, {:d} unsupported, {:d} errors'
                  .format(successes_total, conflicts_total, condition_total, other_total))

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('testdir',
                        help='directory to create micros in')
    parser.add_argument('iterator', choices=['std', 'offset', 'rep', 'val'],
                        help='iterator to generate micros from')
    parser.add_argument('-f', '--fname',
                        help='elf file to extract sequences from')
    parser.add_argument('-n', '--depth', type=int, default=1,
                        help='depth to iterate to')
    parser.add_argument('-m', '--measure', action='store_true',
                        help='actually put timing measurement code in the micros')
    parser.add_argument('-rr', action='store_true',
                        help='reassign registers to avoid conflicts in benchmarks')
    parser.add_argument('-v', '--verbose', type=int, default=1,
                        help='verbosity level')
    parser.add_argument('-ncores', type=int, default=1,
                        help='run in parallel on this many cores')
    args = parser.parse_args()

    main(args)
    exit(0)
