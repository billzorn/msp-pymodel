# elf tools
# supports loading elves into the emulator, and saving emulator state as an elf

import struct
import utils

def nt_string_at(a, i):
    end = a.find(b'\x00', i)
    if end == -1:
        end = len(a)
    return a[i:end].decode('ascii')

def nt_string_append(a, s):
    i = len(a)
    return a + s.encode('ascii') + b'\x00', i

def unpack_schem(schem, fieldnames, data):
    data_struct = struct.unpack(schem, data)
    assert(len(fieldnames) == len(data_struct))
    return {fieldnames[i] : data_struct[i] for i in range(len(fieldnames))}

def pack_schem(schem, fieldnames, fields):
    ordered_fields = (fields[field] if field in fields else 0 for field in fieldnames)
    return struct.pack(schem, *ordered_fields)

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
    return unpack_schem(elf_header_schem, elf_header_fields, a)

def blast_header(f, header):
    header_bytes = pack_schem(elf_header_schem, elf_header_fields, header)
    f.seek(0)
    f.write(header_bytes)

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

def extract_segments(f, header):
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
        prog = unpack_schem(elf_prog_schem, elf_prog_fields, a)
        f.seek(prog['p_offset'])
        prog['data'] = f.read(prog['p_filesz'])
        segments.append(prog)
    return segments

def blast_segments(f, segments, phoff, write_data = True):
    f.seek(phoff)
    for segment in segments:
        segment_bytes = pack_schem(elf_prog_schem, elf_prog_fields, segment)
        f.write(segment_bytes)
    if write_data:
        for segment in segments:
            offset = segment['p_offset']
            filesz = segment['p_filesz']
            data = segment['data'][:filesz]
            f.seek(offset)
            f.write(data)

elf_section_schem = '<10I'
elf_section_fields = [
    'sh_name',
    'sh_type',
    'sh_flags',
    'sh_addr',
    'sh_offset',
    'sh_size',
    'sh_link',
    'sh_info',
    'sh_addralign',
    'sh_entsize',
]

def extract_sections(f, header):
    shoff = header['e_shoff']
    shnum = header['e_shnum']
    shentsize = header['e_shentsize']
    sec_size = struct.calcsize(elf_section_schem)
    if(sec_size != shentsize):
        raise ValueError('bad shentsize in elf: was {:x}, expecting {:x}'.format(shentsize, sec_size))

    sections = []
    for secid in range(shnum):
        f.seek(shoff + secid * sec_size)
        a = f.read(sec_size)
        sec = unpack_schem(elf_section_schem, elf_section_fields, a)
        if sec['sh_type'] in [0, 8]: # SHT_NULL, SHT_NOBITS
            sec['data'] = b''
        else:
            f.seek(sec['sh_offset'])
            sec['data'] = f.read(sec['sh_size'])
        sections.append(sec)
    
    strtab = sections[header['e_shstrndx']]
    for sec in sections:
        if sec['sh_type'] == 0:
            sec['name'] = ''
        else:
            sec['name'] = nt_string_at(strtab['data'], sec['sh_name'])
    return sections

def blast_sections(f, sections, shoff, write_data = True):
    f.seek(shoff)
    for section in sections:
        section_bytes = pack_schem(elf_section_schem, elf_section_fields, section)
        f.write(section_bytes)
    if write_data:
        for section in sections:
            if 'data' in section and len(section['data']) > 0:
                offset = section['sh_offset']
                size = section['sh_size']
                data = section['data'][:size]
                f.seek(offset)
                f.write(data)

elf_symbol_schem = '<3I2BH'
elf_symbol_fields = [
    'st_name',
    'st_value',
    'st_size',
    'st_info',
    'st_other',
    'st_shndx',
]

def symbols_of(sections):
    symtab = None
    for section in sections:
        if section['sh_type'] == 2: # SH_SYMTAB
            symtab = section
            break
    if symtab is None or (not 'data' in symtab):
        return []

    entsize = symtab['sh_entsize']
    sym_size = struct.calcsize(elf_symbol_schem)
    if(sym_size != entsize):
        raise ValueError('bad symbol entsize in elf: was {:x}, expecting {:x}'.format(entsize, sym_size))
    data = symtab['data']
    if len(data) % sym_size != 0:
        raise ValueError('size of symbol table is not divisible by entsize: {:d} % {:d} != 0'.format(len(data), sym_size))

    strtab = sections[symtab['sh_link']]

    symbols = []
    for i in range(0, len(data), sym_size):
        sym = unpack_schem(elf_symbol_schem, elf_symbol_fields, data[i:i+sym_size])
        if sym['st_name'] == 0:
            sym['name'] = ''
        else:
            sym['name'] = nt_string_at(strtab['data'], sym['st_name'])
        symbols.append(sym)
    return symbols

def symbols_pack(symbols):
    a = b''
    for symbol in symbols:
        a += pack_schem(elf_symbol_schem, elf_symbol_fields, symbol)
    return a

elf_section_registers = 0x8000ff01

def load(state, fname, restore_regs = True, verbosity = 0):
    with open(fname, 'rb') as f:
        header = extract_header(f)
        msp_check_header(header)

        # hack to relocate sections based on virtual to physical mapping in prog headers
        v_to_p = {}

        segments = extract_segments(f, header)
        for segment in segments:
            v_to_p[segment['p_vaddr']] = segment['p_paddr']
                
        sections = extract_sections(f, header)
        for section in sections:
            # special section for storing registers from dumps
            if section['sh_type'] == elf_section_registers:
                regdata = section['data']
                r = 0
                for i in range(0, len(regdata), 4):
                    regval = struct.unpack('<I', regdata[i:i+4])
                    state.writereg(r, regval)
                    r += 1

            elif section['sh_flags'] & 0x7 != 0 and section['sh_size'] > 0:
                vaddr = section['sh_addr']
                if vaddr in v_to_p:
                    addr = v_to_p[vaddr]
                else:
                    addr = vaddr
                data = section['data']
                size = section['sh_size']
                
                if verbosity >= 1:
                    if vaddr != addr:
                        vdesc = ' (virtual address {:05x})'.format(vaddr)
                    else:
                        vdesc = ''
                    print('Writing {:5d} bytes at {:05x} [section: {:s}]{:s}...'.format(
                        size, addr, section['name'], vdesc))

                for i in range(min(size, len(data))):
                    state.write8(addr + i, data[i])
                for i in range(max(0, size - len(data))):
                    state.write8(addr + i, 0)

    if verbosity >= 3:
        print('loaded state:')
        state.dump()

save_header = {
    'ei_mag'        : elf_magic,
    'ei_class'      : elf_msp_class,
    'ei_data'       : elf_msp_data,
    'ei_version'    : elf_version,
    'ei_osabi'      : 0,
    'ei_abiversion' : 0,
    'e_type'        : 2, # it's kind of a core file though (4)
    'e_machine'     : elf_msp_machine,
    'e_version'     : elf_version,
    'e_entry'       : None,
    'e_phoff'       : None,
    'e_shoff'       : None,
    'e_flags'       : 0x0,
    'e_ehsize'      : 52,
    'e_phentsize'   : 32,
    'e_phnum'       : None,
    'e_shentsize'   : 40,
    'e_shnum'       : None,
    'e_shstrndx'    : None,
}
save_prog = {
    'p_type'   : 1,
    'p_offset' : None,
    'p_vaddr'  : None,
    'p_paddr'  : None,
    'p_filesz' : None,
    'p_memsz'  : None,
    'p_flags'  : 0x7, # RWE
    'p_align'  : 2,
}
save_section = {
    'sh_name'      : 0,
    'sh_type'      : 1, # PROGBITS
    'sh_flags'     : 0x7, # WAX
    'sh_addr'      : None,
    'sh_offset'    : None,
    'sh_size'      : None,
    'sh_link'      : 0,
    'sh_info'      : 0,
    'sh_addralign' : 2,
    'sh_entsize'   : 0,
}
save_symbol = {
    'st_name'  : None,
    'st_value' : None,
    'st_size'  : 0,
    'st_info'  : 0x3, # STT_SECTION
    'st_other' : 0,
    'st_shndx' : 0xfff1, # SHN_ABS
}

def save(state, fname, verbosity = 0):
    if verbosity >= 3:
        print('saving state:')
        state.dump()

    regions = state.segments()
    phoff = struct.calcsize(elf_header_schem)
    phnum = len(regions)
    header = save_header.copy()
    header['e_phoff'] = phoff
    header['e_phnum'] = phnum
    header['e_entry'] = state.entry()

    name_strtab = '.shstrtab'
    name_symtab = '.symtab'
    s_data = b'\x00'
    s_data, s_name_strtab = nt_string_append(s_data, name_strtab)
    s_data, s_name_symtab = nt_string_append(s_data, name_symtab)

    segments = []
    sections = []
    symbols = []
    # section 0 and symbol 0 are null
    sections.append({})
    symbols.append({})

    offset = phoff + (phnum * struct.calcsize(elf_prog_schem))
    idx = 0
    for addr, data in regions:
        name = '__segment_{:d}'.format(idx)
        s_data, s_name = nt_string_append(s_data, name)

        if verbosity >= 1:
            print('saving {:5d} bytes at {:05x} [section: {:s}]...'.format(
                len(data), addr, name))

        segment = save_prog.copy()
        segment['p_offset'] = offset
        segment['p_vaddr']  = addr
        segment['p_paddr']  = addr
        segment['p_filesz'] = len(data)
        segment['p_memsz']  = len(data)
        segment['data']     = bytes(data)
        segments.append(segment)

        section = save_section.copy()
        section['name']      = name
        section['sh_name']   = s_name
        section['sh_addr']   = addr
        section['sh_offset'] = offset
        section['sh_size']   = len(data)
        section['data']      = bytes(data)
        sections.append(section)

        symbol = save_symbol.copy()
        symbol['name']     = name
        symbol['st_name']  = s_name
        symbol['st_value'] = addr
        symbols.append(symbol)

        offset += len(data)
        idx += 1

    # registers section (for internal use mostly)
    registers = state.registers()
    regdata = b''
    for r in registers:
        regdata += struct.pack('<I', r)
    name_registers = '__registers'
    s_data, s_name_registers = nt_string_append(s_data, name_registers)
    regtab = save_section.copy()
    regtab['name']         = name_registers
    regtab['sh_name']      = s_name_registers
    regtab['sh_type']      = elf_section_registers
    regtab['sh_flags']     = 0x0
    regtab['sh_addr']      = 0
    regtab['sh_offset']    = offset
    regtab['sh_size']      = len(regdata)
    regtab['sh_addralign'] = 4
    regtab['sh_entsize']   = 4
    regtab['data']         = regdata
    sections.append(regtab)
    
    offset += len(regdata)

    # shstrtab section
    strtab = save_section.copy()
    strtab['name']         = name_strtab
    strtab['sh_name']      = s_name_strtab
    strtab['sh_type']      = 3 # SHT_STRTAB
    strtab['sh_flags']     = 0x20 # SHF_STRINGS
    strtab['sh_addr']      = 0
    strtab['sh_offset']    = offset
    strtab['sh_size']      = len(s_data)
    strtab['sh_addralign'] = 1
    strtab['data']         = s_data
    sections.append(strtab)
    strtab_idx = len(sections) - 1

    offset += len(s_data)

    # symtab section
    symdata = symbols_pack(symbols)
    symtab = save_section.copy()
    symtab['name']         = name_symtab
    symtab['sh_name']      = s_name_symtab
    symtab['sh_type']      = 2 # SHT_SYMTAB
    symtab['sh_flags']     = 0x0
    symtab['sh_addr']      = 0
    symtab['sh_offset']    = offset
    symtab['sh_size']      = len(symdata)
    symtab['sh_link']      = strtab_idx
    symtab['sh_info']      = len(symbols)
    symtab['sh_addralign'] = 4
    symtab['sh_entsize']   = struct.calcsize(elf_symbol_schem)
    symtab['data']         = symdata
    sections.append(symtab)

    offset += len(symdata)    

    shoff = offset
    shnum = len(sections)
    header['e_shoff'] = shoff
    header['e_shnum'] = shnum
    header['e_shstrndx'] = strtab_idx
    
    with open(fname, 'wb') as f:
        blast_header(f, header)
        blast_segments(f, segments, phoff, write_data=False)
        blast_sections(f, sections, shoff, write_data=True)

if __name__ == '__main__':
    import msp_fr5969_model as model
    import sys

    if len(sys.argv) != 3:
        print('usage: {:s} <INELF> <OUTELF>'.format(sys.argv[0]))
        exit(1)

    fname = sys.argv[1]
    outfname = sys.argv[2]
    state = model.Model()
    load(state, fname, verbosity=3)
    save(state, outfname, verbosity=1)
