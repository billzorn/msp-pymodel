#!/usr/bin/env python3

import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import msp_micros as micros
import msp_elftools as elftools

def main(args):
    testdir = args.testdir
    n = args.depth
    measure = args.measure
    verbosity = args.verbose

    if args.iterator == 'offset':
        generator = micros.iter_offset(n)
    elif args.iterator == 'rep':
        generator = micros.iter_reps(n)
    else:
        generator = micros.iter_to_depth(n)

    states = micros.iter_states(generator, measure=measure, verbosity=verbosity)
    if verbosity >= 1:
        print('generated {:d} benchmark images'.format(len(states)))
    for i, state in enumerate(states):
        tname = os.path.join(testdir, 't{:d}.elf'.format(i))
        elftools.save(state, tname)        

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
    args = parser.parse_args()

    main(args)
    exit(0)
