#!/usr/bin/env python3

import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import msp_micros as micros
import msp_elftools as elftools

if __name__ == '__main__':
    testdir = sys.argv[1]
    generator = micros.iter_to_depth(2)
    states = micros.iter_states(generator, measure=True)

    for i, state in enumerate(states):
        tname = os.path.join(testdir, 't{:d}.elf'.format(i))
        elftools.save(state, tname)
