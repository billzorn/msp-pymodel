# msp430 isa

import utils
import msp_base as base
import msp_instr as instr
import msp_itable

# decoder

def mk_decode(instrs):
    def most_specified(insns):
        most_bits = 0
        most_ins = None
        for ins in insns:
            specbits = 0
            for bit in ins.bits:
                if bit == 1 or bit == 0:
                    specbits += 1
            if specbits > most_bits:
                most_bits = specbits
                most_ins = ins
        most_count = 0
        for ins in insns:
            specbits = 0
            for bit in ins.bits:
                if bit == 1 or bit == 0:
                    specbits += 1
            if specbits == most_bits:
                most_count += 1
        if most_count > 1:
            print('----')
            print(len(insns))
            for x in insns:
                print(x.bits)
            print('----')
            assert(False)
                
        return most_ins

    def create_node(insns, i):
        if len(insns) == 0:
            return None
        if i == instr.instr_bits:
            return most_specified(insns)
        insns_zero = []
        insns_one = []
        splits = False
        for ins in insns:
            if not ins.bits[i] == 1:
                insns_zero += [ins]
            if not ins.bits[i] == 0:
                insns_one += [ins]
            if ins.bits[i] == 0 or ins.bits[i] == 1:
                splits = True
        if splits:
            return (create_node(insns_zero, i+1),
                    create_node(insns_one, i+1))
        else:
            assert(len(insns) == len(insns_zero) and len(insns) == len(insns_one))
            return (create_node(insns, i+1),)

    instree = create_node(instrs, 0)

    def decode_helper(tree, i, word):
        if isinstance(tree, tuple):
            if len(tree) == 1:
                (inner,) = tree
                return decode_helper(inner, i+1, word)
            else:
                (zero_branch, one_branch) = tree
                if (word >> i) & 1 == 0:
                    return decode_helper(zero_branch, i+1, word)
                else:
                    return decode_helper(one_branch, i+1, word)
        else:
            return tree

    def decode(word):
        return decode_helper(instree, 0, word)
    
    return decode

# isa class

class ISA(object):
    def __init__(self, instrs, fmap):
        self.instrs = instrs
        self.decode = mk_decode(instrs)
        self.name_to_fmt = fmap
        def add_to_map(m, k):
            if not k in m:
                m[k] = len(m)
                return True
            else:
                return False
        # master
        self.fmt_map = {}
        self.fmt_rmap = []
        self.fmt_sizes = []
        # one of each per format
        self.ins_maps = []
        self.smode_maps = []
        self.dmode_maps = []
        self.ins_rmaps = []
        self.smode_rmaps = []
        self.dmode_rmaps = []
        # global instruction tables
        self.ins_ids = {}
        self.ids_ins = []
        for ins in self.instrs:
            if add_to_map(self.ins_ids, ins):
                self.ids_ins += [ins]
            if add_to_map(self.fmt_map, ins.fmt):
                self.fmt_rmap += [ins.fmt]
                self.ins_maps += [{}]
                self.smode_maps += [{}]
                self.dmode_maps += [{}]
                self.ins_rmaps += [[]]
                self.smode_rmaps += [[]]
                self.dmode_rmaps += [[]]
            fmt_idx = self.fmt_map[ins.fmt]
            if add_to_map(self.ins_maps[fmt_idx], ins.name):
                self.ins_rmaps[fmt_idx] += [ins.name]
            if add_to_map(self.smode_maps[fmt_idx], ins.smode):
                self.smode_rmaps[fmt_idx] += [ins.smode]
            if add_to_map(self.dmode_maps[fmt_idx], ins.dmode):
                self.dmode_rmaps[fmt_idx] += [ins.dmode]
        for fmt in self.fmt_rmap:
            fmt_idx = self.fmt_map[fmt]
            self.fmt_sizes += [len(self.ins_rmaps[fmt_idx]) *
                               len(self.smode_rmaps[fmt_idx]) *
                               len(self.dmode_rmaps[fmt_idx])]

            assert(self.fmt_sizes[fmt_idx] == 
                   len(self.ins_maps[fmt_idx]) * 
                   len(self.smode_maps[fmt_idx]) *
                   len(self.dmode_maps[fmt_idx]))

        for ins in self.instrs:
            assert(self.instr_to_idx(ins) == self.instr_modes_to_idx(ins))
            assert(self.idx_to_instr(self.instr_to_idx(ins)) is ins)
            assert(self.idx_to_modes(self.instr_modes_to_idx(ins)) == 
                   (ins.fmt, ins.name, ins.smode, ins.dmode))

    def print_mappings(self):
        for fmt in self.fmt_rmap:
            fmt_idx = self.fmt_map[fmt]
            print('{:s}: ({:d}), {:d} instructions total'.format(fmt, fmt_idx, 
                                                                 self.fmt_sizes[fmt_idx]))
            ins_map = self.ins_maps[fmt_idx]
            smode_map = self.smode_maps[fmt_idx]
            dmode_map = self.dmode_maps[fmt_idx]
            ins_rmap = self.ins_rmaps[fmt_idx]
            smode_rmap = self.smode_rmaps[fmt_idx]
            dmode_rmap = self.dmode_rmaps[fmt_idx]
            print('  {:d} instructions:'.format(len(ins_rmap)))
            for k in ins_rmap:
                print('    {:s} ({:d})'.format(k, ins_map[k]))
            print('  {:d} source modes:'.format(len(smode_rmap)))
            for k in smode_rmap:
                print('    {:s} ({:d})'.format(k, smode_map[k]))
            print('  {:d} destination modes:'.format(len(dmode_rmap)))
            for k in dmode_rmap:
                print('    {:s} ({:d})'.format(k, dmode_map[k]))

    def modes_to_idx(self, fmt, name, smode, dmode):
        fmt_idx = self.fmt_map[fmt]
        offset = sum(self.fmt_sizes[:fmt_idx])
        ins_map = self.ins_maps[fmt_idx]
        smode_map = self.smode_maps[fmt_idx]
        dmode_map = self.dmode_maps[fmt_idx]
        return (ins_map[name] * len(smode_map) * len(dmode_map) +
                smode_map[smode] * len(dmode_map) +
                dmode_map[dmode] + offset)

    def idx_to_modes(self, idx):
        fmt_idx = 0
        i = idx
        while i >= self.fmt_sizes[fmt_idx]:
            i -= self.fmt_sizes[fmt_idx]
            fmt_idx += 1
        return(self.fmt_rmap[fmt_idx],
               self.ins_rmaps[fmt_idx][i // (len(self.smode_rmaps[fmt_idx]) * 
                                             len(self.dmode_rmaps[fmt_idx]))],
               self.smode_rmaps[fmt_idx][(i % (len(self.smode_rmaps[fmt_idx]) * 
                                               len(self.dmode_rmaps[fmt_idx])))
                                          // len(self.dmode_rmaps[fmt_idx])],
               self.dmode_rmaps[fmt_idx][i % len(self.dmode_rmaps[fmt_idx])])

    def modes_to_instr(self, fmt, name, smode, dmode):
        return self.ids_ins[self.modes_to_idx(fmt, name, smode, dmode)]

    def instr_to_modes(self, ins):
        return ins.fmt, ins.name, ins.smode, ins.dmode

    def instr_modes_to_idx(self, ins):
        return self.modes_to_idx(*self.instr_to_modes(ins))
                                            
    def instr_to_idx(self, ins):
        return self.ins_ids[ins]

    def idx_to_instr(self, i):
        return self.ids_ins[i]

    # have to figure out how to do extension words, etc
    def inhabitant(self, ins, fields, check=True):
        words = [ins.inhabit(fields)]
        if 'isrc' in fields:
            words.append(fields['isrc'])
        if 'idst' in fields:
            words.append(fields['idst'])
        if check:
            decoded_ins = self.decode(words[0])
            if not decoded_ins is ins:
                raise ValueError('bad fields: {:s} decoded as {:s}, not {:s}'.format(
                    repr(fields),
                    repr(self.instr_to_modes(decoded_ins)),
                    repr(self.instr_to_modes(ins))))
            minifields = ins.readfields(base.Ministate(words, iswords=True))
            if (('isrc' in fields or ('isrc' in minifields and not 'cgsrc' in minifields))
                and fields['isrc'] != minifields['isrc']):
                raise ValueError('bad isrc: specified {0:d} ({0:#x}), got {1:d} {1:#x}'.format(
                    fields['isrc'], minifields['isrc']))
            if (('idst' in fields or ('idst' in minifields and not 'cgsrc' in minifields))
                and fields['idst'] != minifields['idst']):
                raise ValueError('bad idst: specified {0:d} ({0:#x}), got {1:d} {1:#x}'.format(
                    fields['idst'], minifields['idst']))
        return words

# canonical object
# use these instead of creating your own, as instruction equality works
# by pointer comparison

isa = ISA(msp_itable.create_itable(), msp_itable.create_fmap())

# sanity test
if __name__ == '__main__':
    import sys

    isa.print_mappings()
    print('')
    
    print('test idx <--> modes mapping')

    idxs = set()
    i = 0
    for ins in isa.instrs:
        idx = isa.instr_modes_to_idx(ins)
        assert(isa.modes_to_idx(*isa.idx_to_modes(idx)) == idx)
        if not idx in idxs:
            idxs.add(idx)
            i += 1
    print('  {:d}\tins -> modes -> idx -> modes -> idx'.format(i))

    i = 0
    for idx in range(len(isa.instrs)):
        modes = isa.idx_to_modes(idx)
        assert(isa.idx_to_modes(isa.modes_to_idx(*modes)) == modes)
        i += 1
    print('  {:d}\tidx -> modes -> idx -> modes'.format(i))

    print('test instr <--> id mapping')

    i = 0
    for ins in isa.instrs:
        assert(isa.idx_to_instr(isa.instr_to_idx(ins)) == ins)
        i += 1
    print('  {:d}\tins -> idx -> ins'.format(i))

    i = 0
    for idx in range(len(isa.instrs)):
        assert(isa.instr_to_idx(isa.idx_to_instr(idx)) == idx)
        i += 1
    print('  {:d}\tidx -> ins -> idx'.format(i))

    decode_table = [isa.decode(x) for x in range(2**instr.instr_bits)]
    counts = {}

    for ins in decode_table:
        if ins in counts:
            counts[ins] += 1
        else:
            counts[ins] = 1
    
    print('{:d} decodable instructions (including None: {:d})'.format(len(counts), counts[None]))
    
    utils.print_columns(sorted(['{:5s} {:5s} {:5s}: {:d}'.format(ins.name, ins.smode, ins.dmode, counts[ins]) 
                                for ins in counts if not ins is None]), padding=3)

    for i in range(len(decode_table)):
        prev_ins = False if i-1 < 0 else decode_table[i-1]
        ins = decode_table[i]
        next_ins = False if i+1 >= len(decode_table) else decode_table[i+1]

        descr = 'None' if ins is None else '{:s}\t{:s}\t{:s}'.format(ins.name, ins.smode, ins.dmode)

        if not prev_ins is ins:
            sys.stdout.write('[ {:04x} '.format(i))
            if not next_ins is ins:
                sys.stdout.write('       ] {:s}\n'.format(descr))
        elif not next_ins is ins:
            sys.stdout.write('- {:04x} ] {:s}\n'.format(i,descr))

        
