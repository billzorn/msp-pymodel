# analyzer / generator for historical models

import sys
import os
import pickle

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

from msp_isa import isa
import smt
import historical_models

if __name__ == '__main__':
    statetrans = historical_models.model_m10_full['state_fn_default']

    edges = {}
    for arg, res in smt.split_function_string(statetrans):
        if arg == ('else',):
            state_else = smt.get_state_id(res)
        else:
            tostate = smt.get_state_id(res)
            statestr, iname, rsname, rdname = arg
            fromstate = smt.get_state_id(statestr)
            
            edge = fromstate, tostate
            label = iname, rsname, rdname
            if edge in edges:
                edges[edge].add(label)
            else:
                edges[edge] = {label}

    for k in edges:
        print('{:s} : {:d}'.format(repr(k), len(edges[k])))
        labels = edges[k]
        for label in sorted(labels):
            print('  {:s}'.format(repr(label)))

