#!/usr/bin/env python3

import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import msp_micros as micros
import msp_elftools as elftools
import utils


def iter_states_and_write(args):
    (k, gen, (testdir, measure, verbosity)) = args
    i = 0
    for state in micros.iter_states(gen, measure=measure, verbosity=verbosity):
        tname = os.path.join(testdir, 'p{:d}t{:d}.elf'.format(k, i))
        elftools.save(state, tname)
        i += 1
    if verbosity >= 1:
        print('generated {:d} benchmark images'.format(i))
    return i

def main(args):
    testdir = args.testdir
    n = args.depth
    measure = args.measure
    verbosity = args.verbose
    ncores = args.ncores

    if args.iterator == 'offset':
        generator = micros.iter_offset(n)
    elif args.iterator == 'rep':
        generator = micros.iter_reps(n)
    else:
        generator = micros.iter_to_depth(n)


    if ncores == 1:
        iter_states_and_write((0, generator, (testdir, measure, verbosity)))
    else:
        utils.iter_par(iter_states_and_write, generator, (testdir, measure, verbosity), ncores)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('testdir',
                        help='directory to create micros in')
    parser.add_argument('iterator', choices=['std', 'offset', 'rep'],
                        help='iterator to generate micros from')
    parser.add_argument('-n', '--depth', type=int, default=1,
                        help='depth to iterate to')
    parser.add_argument('-m', '--measure', action='store_true',
                        help='actually put timing measurement code in the micros')
    parser.add_argument('-v', '--verbose', type=int, default=1,
                        help='verbosity level')
    parser.add_argument('-ncores', type=int, default=1,
                        help='run in parallel on this many cores')
    args = parser.parse_args()

    main(args)
    exit(0)
