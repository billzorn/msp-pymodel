#!/usr/bin/env python3

import subprocess
import time
import re

ttyACM_re = re.compile(r'ttyACM([0-9]+)')
ttyinvalid_re = re.compile(re.escape('(error = 57)'))
prompt_re = re.compile(re.escape('(mspdebug)'))

def lsttyACM():
    raw_output = subprocess.check_output(['ls', '/dev'])
    output = raw_output.decode()
    ttys = []
    for line in output.split('\n'):
        m = ttyACM_re.fullmatch(line.strip())
        if m is not None:
            ttys.append(int(m.group(1)))
    return ttys

def detect_driver(k, attempts = 3, retry_delay = 3, verbosity = 0):
    tty = 'ttyACM{:d}'.format(k)

    tries = 0
    while True:

        # attempt to launch mspdebug and look at what it says
        mspdebug = subprocess.Popen(['mspdebug', 'tilib', '-d', tty],
                                    universal_newlines=True,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        stdout_data, stderr_data = mspdebug.communicate(input='exit')

        if ttyinvalid_re.search(stderr_data) is not None:
            return False
        elif prompt_re.search(stdout_data) is not None:
            return True
        else:
            tries += 1
            if verbosity >= 3:
                print('-- mspdebug failed to connect --')
                print(stdout_data)
                print('-- stderr --')
                print(stderr_data)
            if tries < attempts:
                if verbosity >= 2:
                    print('-- retrying (attempt {:d} of {:d}) in {:n} seconds --'
                          .format(tries+1, attempts, retry_delay))
                time.sleep(retry_delay)
            else:
                if verbosity >= 2:
                    print('-- tried to connect {:d} times, returning --'
                          .format(tries))
                return None


def main(args):
    verbosity = args.verbose
    attempts = args.attempts
    delay = args.delay

    ttys = lsttyACM()
    good_ttys = []
    for i in ttys:
        if verbosity >= 2:
            print('Checking ttyACM{:d}...'.format(i))

        detected = detect_driver(i, attempts=attempts, retry_delay=delay, verbosity=verbosity)

        if detected is None:
            if verbosity >= 1:
                print('WARNING: detection failed for ttyACM{:d}.'.format(i))

        if detected:
            if verbosity >= 2:
                print('Success! mspdebug can talk to ttyACM{:d}.'.format(i))
            good_ttys.append(i)
        else:
            if verbosity >= 2:
                print('Failure. nothing to talk to on ttyACM{:d}.'.format(i))
        
    if verbosity >= 1:
        print('\nDone. detected {:d} msp devices:'.format(len(good_ttys)))
        for i in good_ttys:
            print('ttyACM{:d}'.format(i))
        print('')
    
    print(' '.join('ttyACM{:d}'.format(i) for i in good_ttys))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--attempts', type=int, default=3,
                        help='number of times to try connecting to each tty')
    parser.add_argument('-d', '--delay', type=float, default=3.0,
                        help='number of seconds to wait between retries')
    parser.add_argument('-v', '--verbose', type=int, default=0,
                        help='verbosity level')
    args = parser.parse_args()
    
    main(args)
    exit(0)
