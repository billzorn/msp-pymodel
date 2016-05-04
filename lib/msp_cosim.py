# cosimulator: can be parameterized over drivers

import utils

class Cosim(object):
    def __init__(self, drivers, is_physical, mmap):
        if len(drivers) != len(is_physical):
            raise ValueError('Cosim: must provide is_physical for each driver')
        self.is_physical = {drivers[i] : is_physical[i] for i in range(len(drivers))}
        self.drivers = drivers
        self.mmap = mmap

    def diff(self):
        diff = {}
        regdiff = utils.diff_memory([driver.regs() for driver in self.drivers], 0, align=16)
        if len(regdiff) > 0:
            diff['regs'] = regdiff
        for addr, size in self.mmap:
            mems = [driver.md(addr, size) for driver in self.drivers]
            chunks = utils.diff_memory(mems, addr)
            utils.is_diff_real(addr, mems, chunks)
            # assumes no overlap
            for k in chunks:
                diff[k] = chunks[k]
        return diff
        
    # regs and memory
    def sync(self, master_idx, diff = None):
        # print('\n\n')
        # print('syncing diff')
        if diff is None:
            # print('no diff provided, getting')
            diff = self.diff()
        # utils.print_dict(diff)
        # utils.explain_diff(diff)
        # print('\n\n')

        for idx in range(len(self.drivers)):
            if idx != master_idx:
                driver = self.drivers[idx]
                for addr in diff:
                    if addr == 'regs':
                        regdiff = diff['regs']
                        for base_i in regdiff:
                            regvals = regdiff[base_i]
                            for i in range(len(regvals[idx])):
                                if (i < len(regvals[master_idx]) and 
                                    regvals[master_idx][i] != regvals[idx][i]):
                                    driver.setreg(base_i + i, regvals[master_idx][i])
                    else:
                        regions = diff[addr]
                        driver.mw(addr, regions[master_idx])

        # afterdiff = self.diff()
        # if len(afterdiff) > 0:
        #     print('why is there still a diff?')
        #     utils.print_dict(afterdiff)
        #     utils.explain_diff(afterdiff)
        #     print('\n\n')

    def reset(self):
        for driver in self.drivers:
            driver.reset()

    def prog(self, fname):
        for driver in self.drivers:
            driver.prog(fname)

    def mw(self, addr, pattern):
        for driver in self.drivers:
            driver.mw(addr, pattern)

    def fill(self, addr, size, pattern):
        for driver in self.drivers:
            driver.fill(addr, size, pattern)

    def setreg(self, register, value):
        for driver in self.drivers:
            driver.setreg(register, value)

    def md(self, addr, size):
        mems = [driver.md(addr, size) for driver in self.drivers]
        diff = utils.diff_memory(mems, addr)
        return mems, diff

    def regs(self):
        regvals = [driver.regs() for driver in self.drivers]
        regdiff = utils.diff_memory(regvals, 0, align=16)
        return regvals, regdiff

    def step(self):
        for driver in self.drivers:
            driver.step()

    def run(self, max_steps = 10000, interval = 0.5, passes = 1):
        done = True
        for _ in range(passes):
            for driver in self.drivers:
                if self.is_physical[driver]:
                    driver.run(interval=interval)
                else:
                    success, steps = driver.run(max_steps=max_steps)
                    if success and steps >= max_steps:
                        done = False
            if done:
                break
