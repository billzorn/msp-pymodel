# elf loader

# depends on pyelftools:
# https://github.com/eliben/pyelftools
# pip install pyelftools

from elftools.elf.elffile import ELFFile

def extract_foo(elffile):
    print(repr(elffile.header))
    for segment in elffile.iter_segments():
        print(repr(segment.header))
        print(len(segment.data()))

# or not
import struct

elf_header_schem = '<I5B7x2H5I6H'
elf_header_fields = [
    'ei_mag',        # 4
    'ei_class',      # 1
    'ei_data',       # 1
    'ei_version',    # 1
    'ei_osabi',      # 1
    'ei_abiversion', # 1
    'e_type',        # 2
    'e_machine',     # 2
    'e_version',     # 4
    'e_entry',       # 4
    'e_phoff',       # 4
    'e_shoff',       # 4
    'e_flags',       # 4
    'e_ehsize',      # 2
    'e_phentsize',   # 2
    'e_phnum',       # 2
    'e_shentsize',   # 2
    'e_shnum',       # 2
    'e_shstrndx',    # 2
]

def extract_header(f):
    header_size = struct.calcsize(elf_header_schem)
    f.seek(0)
    a = f.read(header_size)
    header_struct = struct.unpack(elf_header_schem, a)
    assert(len(elf_header_fields) == len(header_struct))
    return {elf_header_fields[i] : header_struct[i] for i in range(len(elf_header_fields))}

elf_magic = 0x464c457f
elf_version = 0x1
elf_msp_class = 0x1
elf_msp_data = 0x1
elf_msp_machine = 0x69
def msp_check_header(header):
    if header['ei_mag'] != elf_magic:
        raise ValueError('bad magic number in elf: was {:x}, expecting {:x}'.format(header['ei_mag'], elf_magic))
    if header['ei_version'] != elf_version:
        raise ValueError('bad elf version: was {:x}, expecting {:x}'.format(header['ei_version'], elf_version))
    if header['ei_class'] != elf_msp_class:
        raise ValueError('bad elf class: was {:x}, expecting {:x}'.format(header['ei_class'], elf_msp_class))
    if header['ei_data'] != elf_msp_data:
        raise ValueError('bad elf endianness: was {:x}, expecting {:x}'.format(header['ei_data'], elf_msp_data))
    if header['e_machine'] != elf_msp_machine:
        raise ValueError('bad machine identifier in elf: was {:x}, expecting {:x}'.format(header['e_machine'], elf_msp_machine))
    return

elf_prog_schem = '<8I'
elf_prog_fields = [
    'p_type',
    'p_offset',
    'p_vaddr',
    'p_paddr',
    'p_filesz',
    'p_memsz',
    'p_flags',
    'p_align',
]

def extract_segments(f):
    header = extract_header(f)
    phoff = header['e_phoff']
    phnum = header['e_phnum']
    phentsize = header['e_phentsize']
    prog_size = struct.calcsize(elf_prog_schem)
    if(prog_size != phentsize):
        raise ValueError('bad phentsize in elf: was {:x}, expecting {:x}'.format(phentsize, prog_size))
    
    segments = []
    for segid in range(phnum):
        f.seek(phoff + segid * prog_size)
        a = f.read(prog_size)
        prog_struct = struct.unpack(elf_prog_schem, a)
        assert(len(elf_prog_fields) == len(prog_struct))
        prog = {elf_prog_fields[i] : prog_struct[i] for i in range(len(elf_prog_fields))}
        f.seek(prog['p_offset'])
        prog['data'] = f.read(prog['p_filesz'])
        segments.append(prog)
    return segments

def load(state, fname):
    with open(fname, 'rb') as f:
        header = extract_header(f)
        msp_check_header(header)
        for segment in extract_segments(f):
            addr = segment['p_paddr']
            size = segment['p_memsz']
            data = segment['data']
            for i in range(min(size, len(data))):
                state.write8(addr + i, data[i])
            for i in range(max(0, size - len(data))):
                state.write8(addr + i, 0)

if __name__ == '__main__':

    import msp_fr5969_model as model

    import sys
    if len(sys.argv) != 2:
        print('usage: {:s} <ELF>'.format(sys.argv[0]))
        exit(0)

    fname = sys.argv[1]
    state = model.Model()
    state.dump()
    load(state, fname)
    state.dump()
