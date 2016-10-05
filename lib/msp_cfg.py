# basic block timing analysis

import utils
import msp_base as base
import msp_fr5969_model as model
import msp_elftools as elftools
from msp_isa import isa
import msp_instr as instr

class BasicBlock(object):
    def __init__(self, addr, verbosity = 0):
        self.addr = addr
        self.instrs = []
        self.callsites = set()
        self.preds = set()
        self.succs = set()
        self.call_return_target = None
        if verbosity >= 2:
            print('   NEW bblock {:05x}'.format(addr))

    def __str__(self):
        s =  'BB at {:05x}\n'.format(self.addr)
        s += '  under: '
        first = True
        for callsite in sorted(self.callsites):
            if first:
                first = False
            else:
                s += '         '
            s += '{:05x}\n'.format(callsite)
        s += '  preds:\n'
        for pred in sorted(self.preds):
            s += '    {:05x}\n'.format(pred)
        s += '  succs:\n'
        for succ in sorted(self.succs):
            s += '    {:05x}\n'.format(succ)
        if self.call_return_target is not None:
            s += '  call returns to {:05x}\n'.format(self.call_return_target)
        return s


class CallSite(object):
    def __init__(self, addr, verbosity = 0):
        self.addr = addr
        self.bblock = None
        self.children = set()
        self.return_targets = set()
        self.callees = set()
        if verbosity >= 2:
            print('   NEW site {:05x}'.format(addr))

    def __str__(self):
        s =  'CallSite at {:05x}\n'.format(self.addr)
        s += '  callees:\n'
        for callee in sorted(self.callees):
            s += '    {:05x}\n'.format(callee)
        s += '  return_targets:\n'
        for rt in sorted(self.return_targets):
            s += '    {:05x}\n'.format(rt)
        s += '  children:\n'
        for child in sorted(self.children):
            s += '    {:05x}\n'.format(child)
        if self.bblock is not None:
            # s += '-- entry block --\n{:s}'.format(str(self.bblock))
            s += '-- entry block --\n'
        else:
            s += '-- no entry block recorded --\n'
        return s


class CFG(object):
    def __init__(self, fname, verbosity = 0):
        self.verbosity = verbosity
        self.state = model.Model()
        self.read16 = model.mk_read16(self.state.read8)

        # TODO: alternative to readfields that doesn't always crash?
        for addr in range(4096):
            self.state.mmio_handle_default(addr)

        if self.verbosity >= 1:
            print('loading {:s}'.format(fname))
        elftools.load(self.state, fname, restore_regs=False, verbosity=self.verbosity)

    def _describe(self, call_table, block_table, entrypoint):
        print('CFG starting from {:05x}, {:d} sites, {:d} basic blocks\n'
              .format(entrypoint, len(call_table), len(block_table)))
        ct_clone = call_table.copy()
        bt_clone = block_table.copy()
        self._describe_call(ct_clone, bt_clone, entrypoint)
        if ct_clone or bt_clone:
            while ct_clone:
                print('REMAINING: {:d} sites, {:d} basic blocks\n'
                      .format(len(ct_clone), len(bt_clone)))
                first = sorted(ct_clone.keys())[0]
                self._describe_call(ct_clone, bt_clont, first)
            while bt_clone:
                print('REMAINING: {:d} sites, {:d} basic blocks\n'
                      .format(len(ct_clone), len(bt_clone)))
                first = sorted(bt_clone.keys())[0]
                self._describe_block(bt_clone, first)
        else:
            print('No unreachable blocks, good')

    def _describe_call(self, call_table, block_table, call_addr):
        callsite_object = call_table.pop(call_addr, None)
        if callsite_object is None:
            print('Already visited site {:05x}\n'.format(call_addr))
        else:
            print(str(callsite_object))
            self._describe_block(block_table, call_addr)
            for addr in sorted(callsite_object.callees):
                self._describe_call(call_table, block_table, addr)

    def _describe_block(self, block_table, block_addr):
        block_object = block_table.pop(block_addr, None)
        if block_object is None:
            print('Already visited block {:05x}\n'.format(block_addr))
        else:
            print(str(block_object))
            addr = block_object.call_return_target
            if addr is not None:
                self._describe_block(block_table, addr)
            else:
                for addr in sorted(block_object.succs):
                    self._describe_block(block_table, addr)

    def _describe_workset(self, workset):
        print('Workset: {:d} blocks to process'.format(len(workset)))
        for pc, callsite, pc_pred in workset:
            print('  pc {:05x}, under {:05x}, from {:05x}'
                  .format(pc, callsite, pc_pred))
        print('')

    def build_graph(self, do_quadratic_checks = False):
        # find entry point
        entrypoint = self.read16(model.resetvec)
        entrysite = CallSite(entrypoint, self.verbosity)

        # tables of observed call sites and blocks
        call_table = {entrypoint : entrysite}
        block_table = {}

        # tables of covered instructions and memory sites
        ins_table = {}
        byte_table = {}

        # set of pc values to consider next
        workset = { (entrypoint, entrypoint, model.resetvec) }
        def update_workset(pc, callsite, pc_pred):
            if pc not in block_table or callsite not in block_table[pc].callsites:
                if self.verbosity >= 3:
                    print('    pushed {:05x} under {:05x}, from {:05x}'.format(pc, callsite, pc_pred))
                workset.add( (pc, callsite, pc_pred) )
            # pc and callsite already matched, update preds only
            else:
                block_table[pc].preds.add(pc_pred)
        # could maintain a separate index if this is needed as a feature
        if do_quadratic_checks:
            def pc_in_workset(pc_check):
                return any(pc == pc_check for pc, callsite, pc_pred in workset)

        while workset:
            pc, callsite, pc_pred = workset.pop()
            if self.verbosity >= 3:
                print('    popped {:05x} under {:05x}, from {:05x}'.format(pc, callsite, pc_pred))

            # we might be seeing the same block again under a different callsite,
            # as callsites can overlap...
            if pc in block_table:
                if self.verbosity >= 2:
                    print('   DUPE bblock {:05x}'.format(pc))
                current_block = block_table[pc]

                #assert callsite not in current_block.callsites
                # This assertion doesn't make sense, in the case where we add multiple entries
                # to a new block under the same callsite but different PCs, for example in the case
                # where we just split.

                current_block.callsites.add(callsite)
                current_block.preds.add(pc_pred)
                # put all of the block's non-call successors back onto the worklist with the new callsite
                pc_target = current_block.call_return_target
                if pc_target is not None:
                    update_workset(pc_target, callsite, current_block.addr)
                else:
                    for pc_target in current_block.succs:
                        update_workset(pc_target, callsite, current_block.addr)
                continue
                # and done with this block
            
            current_block = BasicBlock(pc, verbosity=self.verbosity)
            current_block.callsites.add(callsite)
            current_block.preds.add(pc_pred)
            block_table[pc] = current_block

            # check if this is the entry point of a new callsite: should only happen once
            callsite_object = call_table[callsite]
            if callsite == pc:
                assert callsite_object.bblock == None, 'callsite {:05x} has already seen pc'.format(callsite)
                callsite_object.bblock = current_block
            callsite_object.children.add(pc)

            in_block = True
            split_addr = None
            while in_block:
                word = self.read16(pc)
                ins = isa.decode(word)

                # check the validity of the decoding
                if ins is None:
                    raise ValueError('unable to decode word {:04x} at {:05x}, skipping'
                                     .format(word, pc))

                # note that AI will change the registers...
                self.state.writereg(0, pc)
                fields = ins.readfields(self.state)
                pc_next = instr.pcadd(pc, ins.length)
                if self.verbosity >= 4:
                    print('      pc {:05x}, len({:d}), next {:05x}'.format(pc, ins.length, pc_next))

                # check if we've visited this memory before, split if we have
                if pc in ins_table:
                    prev_addr = ins_table[pc]
                    if split_addr is None:
                        split_addr = prev_addr
                        if prev_addr == current_block.addr:
                            if self.verbosity >= 2:
                                print('post split: revisiting {:05x} in block {:05x} again'
                                      .format(pc, prev_addr))
                        else:
                            if self.verbosity >= 2:
                                print('split: revisiting {:05x} in block {:05x}, first visit from block {:05x}'
                                      .format(pc, current_block.addr, ins_table[pc]))

                            # to split we just remove the existing block and put it back on the worklist.
                            # the fallthrough logic will connect back to the new block automatically.
                            if prev_addr in block_table:                                
                                prev_block = block_table.pop(prev_addr)
                                # remove from children of callsites --
                                # the update logic should re-add everything, not clear if this is necessary
                                for old_callsite in prev_block.callsites:
                                    old_callsite_object = call_table[old_callsite]
                                    if old_callsite_object.bblock is prev_block:
                                        old_callsite_object.bblock = None
                                    if prev_addr in old_callsite_object.children:
                                        old_callsite_object.children.remove(prev_addr)
                                    else:
                                        print('WARNING: old site {:05x} missing child {:05x}'
                                              .format(old_callsite, prev_addr))
                                # don't remove from predecessors,
                                for old_pred in prev_block.preds:
                                    # just put back on worklist for each pred, for each of that pred's callsites
                                    for old_callsite in prev_block.callsites:
                                        update_workset(prev_addr, old_callsite, old_pred)
                            else:
                                # if we couldn't find the block, we must have already removed it and it's
                                # somewhere in the worklist
                                if do_quadratic_checks:
                                    assert pc_in_workset(prev_addr), ('previously removed {:05x} missing from workset'
                                                                      .format(prev_addr))
                                    check_str = ' (found {:05x} in workset)'.format(prev_addr)
                                else:
                                    check_str = ''
                                if self.verbosity >= 2:
                                    print('already removed {:05x} for a previous split'.format(prev_addr, check_str))
                    else:
                        if split_addr != prev_addr:
                            if do_quadratic_checks:
                                assert pc_in_workset(prev_addr), ('was splitting {:05x}, saw {:05x} not in workset'
                                                                  .format(split_addr, prev_addr))
                                check_str = ' (found {:05x} in workset)'.format(prev_addr)
                            else:
                                check_str = ''
                            if self.verbosity >= 2:
                                print('splits overlap: was splitting {:05x}, saw {:05x}{:s}'
                                      .format(split_addr, prev_addr, check_str))
                            # update split_addr to track multiple overlaps instead of just creating spam
                            split_addr = prev_addr

                            # #self._describe(call_table, block_table, entrypoint)
                            # self._describe_workset(workset)
                            # for i in range(pc, pc + 32):
                            #     if i in ins_table:
                            #         print(' {:05x} : {:05x}'.format(i, ins_table[i]))
                            #     else:
                            #         print(' {:05x} : None'.format(i))
                            # assert False
                ins_table[pc] = current_block.addr

                for b in range(pc, pc_next):
                    if b in byte_table:
                        assert split_addr == prev_addr, 'byte splitting {:05x}, saw {:05x}'.format(split_addr, prev_addr)
                    byte_table[b] = current_block.addr
                
                current_block.instrs.append(ins)
                
                if ins.fmt in {'jump'}:
                    offset = fields['jump_offset']
                    # jump offsets are actually relative to the fallthrough pc
                    pc_target = instr.pcadd(pc_next, offset)
                    current_block.succs.add(pc_target)
                    update_workset(pc_target, callsite, current_block.addr)
                    if ins.name not in {'JMP'}:
                        current_block.succs.add(pc_next)
                        update_workset(pc_next, callsite, current_block.addr)
                    in_block = False

                elif ins.name in {'CALL'}:
                    if ins.smode in {'#N', '#@N'}:
                        pc_call_target = fields['src']
                        
                        # create a new callsite for this call target if we don't already have one
                        if pc_call_target not in call_table:
                            callsite_object_target = CallSite(pc_call_target, verbosity=self.verbosity)
                            call_table[pc_call_target] = callsite_object_target
                        else:
                            callsite_object_target = call_table[pc_call_target]
                            
                        # we'll update that callsite's bblock and children when we pull this target
                        # pc out of the workset

                        # update return targets and callees
                        callsite_object_target.return_targets.add(pc_next)
                        current_block.call_return_target = pc_next
                        callsite_object.callees.add(pc_call_target)

                        # update the workset with both the call and return targets
                        current_block.succs.add(pc_call_target)
                        update_workset(pc_call_target, pc_call_target, current_block.addr)
                        current_block.succs.add(pc_next)
                        update_workset(pc_next, callsite, current_block.addr)
                        
                    else:
                        if self.verbosity >= 0:
                            print('indirect call at {:05x}, unsupported'.format(pc))
                    in_block = False
                
                # check for indirect branch
                elif ins.name in {'MOV'} and ins.dmode in {'Rn'} and fields['rdst'] in {0}:
                    # emulated return
                    if ins.smode in {'@Rn+'} and fields['rsrc'] in {1}:
                        pass

                        # we've already captured the return targets when we entered the callsite,
                        # nothing else to do

                    elif ins.smode in {'#N', '#@N'}:
                        pc_target = fields['src']
                        current_block.succs.add(pc_target)
                        update_workset(pc_target, callsite, current_block.addr)

                    else:
                        if self.verbosity >= 0:
                            print('indirect branch at {:05x}, unsupported'.format(pc))
                    in_block = False

                # look at next instruction in block
                else:
                    pc = pc_next

                    # check to make sure we aren't merging with an existing block
                    if pc in block_table:
                        if self.verbosity >= 2:
                            print('fallthrough edge from block {:05x} to {:05x}'.format(current_block.addr, pc))
                        current_block.succs.add(pc)
                        update_workset(pc, callsite, current_block.addr)
                        in_block = False

            if self.verbosity >= 4:
                print('created:')
                print(str(current_block))

        if self.verbosity >= 1:
            print('processed workset, {:d} callsites, {:d} blocks'.format(len(call_table), len(block_table)))
            print('covered {:d} instructions, {:d} bytes'.format(len(ins_table), len(byte_table)))
            self._describe(call_table, block_table, entrypoint)


    def check_instrs(self):
        pc = self.read16(model.resetvec)
        word = self.read16(pc)

        while word != 0x3fff and pc < model.upper_start + model.upper_size:
            ins = isa.decode(word)
            if ins is None:
                print('{:05x} unable to decode instruction: {:04x}'
                      .format(pc, word))
                pc += 2
            else:
                print('{:05x}'.format(pc), ins.fmt, ins.name, ins.smode, ins.dmode)
                pc += ins.length
            word = self.read16(pc)

if __name__ == '__main__':
    import sys
    fname = sys.argv[1]
    cfg = CFG(fname, verbosity=1)
    
    cfg.build_graph(do_quadratic_checks=True)
