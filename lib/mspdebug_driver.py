# controller for mspdebug subprocess (that can talk to an actual msp430 chip)

import sys
import re
import subprocess
import time
import signal

import utils

######################################################################
# non-blocking read support for subproces.PIPE
# see: http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python 
######################################################################

# I'm proud to say that this is probably the worst code I've ever written...

from threading import Thread
from queue import Queue, Empty

# enqueue at 120fps
enq_sleeptime = 1.0 / 120.0

# read at 60fps
default_timeout = 1.0 / 60.0
default_retries = int(10 / default_timeout)

def enqueue_output(out, queue):
    while True:
        c = out.read(1)
        while c != '':
            queue.put(c)
            c = out.read(1)
        time.sleep(enq_sleeptime)

# don't pass a different timeout, retries gives the timeout in increments of 1/60 second
# also note that retries only matters if there's a target, otherwise we only
# go around once anyway
def nonblocking_read(queue, target = None, timeout = default_timeout, retries = default_retries,
                     verbosity = 0):
    output = ''
    first = True
    tries = 0
    if verbosity >= 3:
        print('NBR', end='')
        sys.stdout.flush()
    while first or ((not target is None) and re.search(target, output) is None):
        first = False
        got_output = False
        try:
            while True:
                output += queue.get(block=(timeout > 0), timeout=timeout)
                got_output = True
        except Empty:
            pass
        if not got_output:
            if verbosity >= 3:
                print('.', end='')
                sys.stdout.flush()
            tries += 1
            if tries >= retries:
                break
        elif verbosity >= 3:
            print(':', end='')
            sys.stdout.flush()
        
    if verbosity >= 3:
        print('')
    return output

# yeah... should really use the asyncio interface from python3 or whatever

######################################################################

class MSPdebug(object):
    def __init__(self, tty = None, verbosity = 0):
        self.verbosity = verbosity
        if self.verbosity >= 3:
            print(str(self) + ' created')
        self.tty = tty
        mspargs = ['mspdebug', 'tilib']
        if not self.tty is None:
            mspargs += ['-d', str(tty)]

        # regexes used to control reading
        self.prompt_re = re.compile(re.escape('(mspdebug)'))
        self.run_re = re.compile(re.escape('Running. Press Ctrl+C to interrupt...'))
        self.exit_re = re.compile(re.escape('MSP430_Close'))

        # the Popen object itself
        self.mspdebug = subprocess.Popen(mspargs, universal_newlines=True, stdin=subprocess.PIPE, 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # massive pile of threading code for nonblocking IO
        self.stdout_q = Queue()
        self.stdout_t = Thread(target=enqueue_output, args=(self.mspdebug.stdout, self.stdout_q))
        self.stdout_t.daemon = True
        self.stdout_t.start()
        self.stderr_q = Queue()
        self.stderr_t = Thread(target=enqueue_output, args=(self.mspdebug.stderr, self.stderr_q))
        self.stderr_t.daemon = True
        self.stderr_t.start()
        
        # wait until the connection is established and throw away startup output
        startup_output = self._response()
        if self.verbosity >= 4:
            print(startup_output)

    # core interface

    def _issue_cmd(self, cmd):
        if self.verbosity >= 1:
            print('sending: ' + cmd)
        self.mspdebug.stdin.write(cmd + '\n')
        self.mspdebug.stdin.flush()

    def _read_stdout(self, target = None, retries = default_retries):
        if self.verbosity >= 3:
            if target is None:
                target_str = ''
            else:
                target_str = ' (until ' + target.pattern + ')'
            print('-- reading from stdout{:s} (retries={:d}) --'.format(target_str, retries))
        output = nonblocking_read(self.stdout_q, target=target, retries=retries, 
                                  verbosity=self.verbosity)
        if self.verbosity >= 3:
            print(utils.summarize_triple(output))
            print('----')
        return output

    def _read_stderr(self, target = None, retries = default_retries):
        if self.verbosity >= 3:
            if target is None:
                target_str = ''
            else:
                target_str = ' (until ' + target.pattern + ')'
            print('-- reading from stderr{:s} (retries={:d}) --'.format(target_str, retries))
        output = nonblocking_read(self.stdout_q, target=target, retries=retries,
                                  verbosity=self.verbosity)
        if self.verbosity >= 3:
            print(utils.summarize_triple(output))
            print('----')
        return output
    
    # context manager interface

    def _close(self):
        if self.verbosity >= 2:
            print('Killing mspdebug...')
        self._issue_cmd('exit')
        self._read_stdout(target=self.exit_re)
        stderr_output = self._read_stderr()
        if len(stderr_output) > 0:
            print('Unexpected output from mspdebug on stderr:')
            print(stderr_output)
        try:
            self.mspdebug.communicate()
        except IOError as e:
            if self.verbosity >= 2:
                print('Bad concurrent IO:')
                print(e)
        except Exception as e:
            if self.verbosity >= 0:
                print('Unexpected exception:')
                print(e)
        finally:
            if self.mspdebug.poll() is None:
                if self.verbosity >= 2:
                    print('mspdebug did not shut itself down, sending SIGTERM')
                term = self.mspdebug.terminate()
                if self.verbosity >= 2:
                    print(str(term))
            if self.verbosity >= 2:
                print('... Done.')

    def __enter__(self):
        if self.verbosity >= 3:
            print(str(self) + ' passed into context')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.verbosity >= 3:
            print(str(self) + ' exiting')
        self._close()

    # internal helpers

    def _response(self):
        output = self._read_stdout(target=self.prompt_re)
        output_stderr = self._read_stderr()

        if len(output_stderr) > 0:
            print('WARNING: unexpected output from mspdebug on stderr:')
            print(output_stderr)

        prompt_match = re.search(self.prompt_re, output)
        if prompt_match is None:
            return output
        i = prompt_match.start()
        if 0 <= i < len(output):
            return output[0:i].strip()
        else:
            return output

    def _await_run(self):
        self._read_stdout(target=self.run_re)
        output_stderr = self._read_stderr()

        if len(output_stderr) > 0:
            print('WARNING: unexpected output from mspdebug on stderr:')
            print(output_stderr)

        return

    def _interrupt(self):
        self.mspdebug.send_signal(signal.SIGINT)
        return self._response()

    # external interface

    def reset(self):
        self._issue_cmd('reset')
        self._response()

    def prog(self, fname):
        self._issue_cmd('prog {:s}'.format(fname))
        self._response()

    def mw(self, addr, pattern):
        self._issue_cmd(('mw {:#x}' + (' {:#x}' * len(pattern))).format(addr, *pattern))
        self._response()

    def fill(self, addr, size, pattern):
        self._issue_cmd(('fill {:#x} {:d}' + (' {:#x}' * len(pattern))).format(addr, size, *pattern))
        self._response()
    
    def setreg(self, register, value):
        self._issue_cmd('set {:d} {:#x}'.format(register, value))
        self._response()

    def md(self, addr, size):
        self._issue_cmd('md {:#x} {:d}'.format(addr, size))
        return utils.parse_memory(self._response())

    def regs(self):
        self._issue_cmd('regs')
        return utils.parse_regs(self._response())

    def step(self):
        self._issue_cmd('step')
        self._response()

    def run(self, interval = 0.5):
        self._issue_cmd('run')
        self._await_run()
        time.sleep(interval)
        self._interrupt()

# thin wrapper for basic mspdebug usage
if __name__ == '__main__':
    def print_with_spacer(text):
        spacer = '=' * 80
        print(spacer)
        print(text)
        print(spacer)

    with MSPdebug(verbosity=5) as driver:
        # register sigint handler to relay SIGINT to mspdebug
        # not needed?
        def sigint_handler(signum, frame):
            print('caught signal {:d}'.format(signum))
            output = driver._interrupt()
            print_with_spacer(output)

        # prompt the user
        def prompt():
            print('> ', end='')
            sys.stdout.flush()

        # relay commands from user
        prompt()
        for line in sys.stdin:
            cmd = line.strip()

            print('cmd: {:s}'.format(repr(cmd)))

            if cmd == 'exit':
                print('exiting')
                break
            elif cmd == 'run':
                print('running')
                driver._issue_cmd(cmd)
                driver._await_run()
                signum = signal.sigwait([signal.SIGINT])
                sigint_handler(signum, None)
            elif cmd == 'borken':
                driver._issue_cmd('help')
                output = driver._read_stdout(target=driver.exit_re, retries=100)
                print_with_spacer(output)
            elif cmd == 'borken2':
                driver._issue_cmd('md 0 4096')
                output = driver._read_stdout(target=driver.exit_re, retries=25)
                print_with_spacer(output)
            elif cmd == 'borclean':
                output = driver._read_stdout(target=re.compile(r'(?!x)x'), retries=100)
                print_with_spacer(output)
            else:
                print('issuing')
                driver._issue_cmd(cmd)
                output = driver._response()
                print_with_spacer(output)

            prompt()

        print('goodbye')
