# handy things

import shutil
import re

def boring_region(fill, align):
    region = fill * (align // len(fill))
    if len(region) < align:
        region += fill
    if len(region) > align:
        region = region[:align]
    return region

def boring_region_description(fill, align):
    region_description = '[' + (' {:02x}' * len(fill)).format(*fill) + ' ]'
    return boring_region(fill, align), region_description

def interesting_regions(mem, addr, fill = [0x0], align = 8):
    boring = boring_region(fill, align)
    regions = []

    start_idx = 0
    for idx in range(0, len(mem), align):
        if mem[idx:idx+align] == boring:
            if start_idx < idx:
               regions.append((addr + start_idx, mem[start_idx:idx]))
            start_idx = idx + align
    if start_idx < len(mem):
        regions.append((addr + start_idx, mem[start_idx:]))
    return regions

unprintable_re = re.compile(r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~ ]')

def describe_regs(regs):
    regstr = '( PC: {:05x}) ( R4: {:05x}) ( R8: {:05x}) (R12: {:05x})\n'.format(
        regs[0], regs[4], regs[8], regs[12])
    regstr += '( SP: {:05x}) ( R5: {:05x}) ( R9: {:05x}) (R13: {:05x})\n'.format(
        regs[1], regs[5], regs[9], regs[13])
    regstr += '( SR: {:05x}) ( R6: {:05x}) (R10: {:05x}) (R14: {:05x})\n'.format(
        regs[2], regs[6], regs[10], regs[14])
    regstr += '( R3: {:05x}) ( R7: {:05x}) (R11: {:05x}) (R15: {:05x})'.format(
        regs[3], regs[7], regs[11], regs[15])
    return regstr

# will probably also add a parser that goes the other direction
def describe_memory_row(mem, addr, idx, cols = 16):
    used_cols = min(cols, len(mem) - idx)
    unused_cols = cols - used_cols
    bin_fmt = '{:05x}:' + (' {:02x}' * used_cols) + ('   ' * unused_cols)
    str_fmt = ('{:s}' * used_cols) + (' ' * unused_cols)
    row_values = mem[idx:idx+used_cols]

    return (bin_fmt.format(addr + idx, *row_values) + ' |' +
            re.sub(unprintable_re, '.', str_fmt.format(*map(chr, row_values))) + '|')

def describe_memory(mem, addr, cols = 16):
    memstr = ''
    for idx in range(0, len(mem), cols):
        memstr += describe_memory_row(mem, addr, idx, cols = cols)
        if idx < len(mem) - cols:
            memstr += '\n'
    return memstr

def describe_interesting_memory(mem, addr, fill = [0xff], cols=16):
    memstr = ''
    boring_row, fill_description = boring_region_description(fill, cols)
           
    boring_count = 0
    for idx in range(0, len(mem), cols):
        used_cols = min(cols, len(mem) - idx)
        unused_cols = cols - used_cols
        row_values = mem[idx:idx+used_cols]
        if row_values == boring_row:
            boring_count += 1
        else:
            if boring_count > 0:
                memstr += '{:s} for {:d} bytes ({:d} rows)\n'.format(fill_description, boring_count * cols, boring_count)
                boring_count = 0
            memstr += describe_memory_row(mem, addr, idx, cols = cols)
            if idx < len(mem) - cols:
                memstr += '\n'
    if boring_count > 0:
        memstr += '{:s} for {:d} bytes ({:d} rows)'.format(fill_description, boring_count * cols, boring_count)
    return memstr

def summarize_interesting(description, fill = [0xff], cols=16):
    summary = ''
    boring_row, fill_description = boring_region_description(fill, cols)

    boring_count = 0
    description_lines = description.split('\n')
    for i in range(len(description_lines)):
        line = description_lines[i]
        try:
            bin_formatted = line.split('|')[0]
            bytes_str = bin_formatted.split(':')[1].strip()
            row_values = [int(s, 16) for s in bytes_str.split()]
        except Exception:
            row_values = None
        if row_values == boring_row:
            boring_count += 1
        else:
            if boring_count > 0:
                summary += '{:s} for {:d} bytes ({:d} rows)\n'.format(fill_description, boring_count * cols, boring_count)
                boring_count = 0
            summary += line.strip()
            if i < len(description_lines) - 1:
                summary += '\n'
    if boring_count > 0:
        summary += '{:s} for {:d} bytes ({:d} rows)'.format(fill_description, boring_count * cols, boring_count)
    return summary

def explain_bitval(firstbit, lastbit, bitval, bits = 16):
    print('({:d}, {:d}) : {:d} [{:d}]'.format(firstbit, lastbit, bitval, bits))

    if 0 > firstbit or firstbit > lastbit or lastbit > (bits - 1):
        print('  nonsense bitrange {:d} - {:d}'.format(firstbit, lastbit))
        return

    field_bits = lastbit - firstbit + 1
    if field_bits <= 0:
        print('  nonsense field_bits {:d}'.format(field_bits))
        return

    max_bitval = (2 ** field_bits) - 1
    if bitval > max_bitval:
        print('  bitval does not fit in field: {:d} > 2 ** {:d} - 1 == {:d}'.format(bitval, field_bits, max_bitval))
        return

    print('  val {:x}'.format(bitval))
    
    l_bits = bits - 1 - lastbit
    r_bits = firstbit
    print(('  bin {:s}{:0' + str(field_bits) + 'b}{:s}').format('x'*l_bits, bitval, 'x'*r_bits))

    firstnybble = firstbit // 4
    lastnybble = lastbit // 4
    field_nybbles = lastnybble - firstnybble + 1
    nybbles = bits // 4
    adjusted_bitval = bitval << (firstbit - (firstnybble * 4))
    l_nybbles = nybbles - lastnybble - 1
    r_nybbles = firstnybble
    print(('  hex {:s}{:0' + str(field_nybbles) + 'x}{:s}').format('x'*l_nybbles, adjusted_bitval, 'x'*r_nybbles))
    return

def print_columns(lines, columns = None, padding = 1, ralign = False):
    segments = []
    maxlen = 0

    for line in lines:
        s = str(line)
        maxlen = max(maxlen, len(s))
        segments.append(s)

    try:
        termsz = shutil.get_terminal_size()
        termwidth, _ = termsz
    except:
        termwidth = 0

    fieldwidth = maxlen + padding
    if columns is None:
        columns = max((termwidth + padding) // fieldwidth, 1)
    rows = len(segments) // columns
    if rows * columns < len(segments):
        rows += 1

    for r in range(rows):
        for c in range(columns):
            i = c * rows + r
            if i < len(segments):
                segment = segments[i]
                padlen = fieldwidth - len(segment)
                if ralign:
                    print(' '*(padlen-1), segment, end='')
                else:
                    print(segment, ' '*(padlen-1), end='')
            else:
                break
        print('')
    
    if rows * columns > len(segments):
        print('')
    
def print_dict(d, indent = 0):
    try:
        termsz = shutil.get_terminal_size()
        termwidth, _ = termsz
    except:
        termwidth = 80

    if indent == 0:
        print('<dict with {:d} entries>'.format(len(d)))
        indent += 2

    width = termwidth - indent
    max_k_width = max(width // 4, 10)

    subdicts = []
    sorted_kvs = []
    k_len = 0
    ellipsis = '\u2026'
    
    for k in sorted(d):
        v = d[k]
        if isinstance(v, dict):
            subdicts.append((str(k), v))
        else:
            k_str = str(k)
            k_len = max(k_len, len(k_str))
            sorted_kvs.append((k_str, v))

    if k_len > max_k_width:
        k_len = max_k_width
    v_len = max(width - k_len - 3, 10)

    for k, v in sorted_kvs:
        if len(k) > k_len:
            k_str = k[:k_len - 1] + ellipsis
        else:
            k_str = k

        # try to give sizes of arrays and stuff
        try:
            size = len(v)
            classtype = type(v)
            v_str = '{:s} of length {:d}> {:s}'.format(str(classtype)[:-1], size, repr(v))
        except Exception:
            v_str = str(v)
        if len(v_str) > v_len:
            v_str = v_str[:v_len - 1] + ellipsis

        print(('{:s}{:' + str(k_len) + 's} : {:s}').format(' ' * indent, k_str, v_str))

    for k, subd in subdicts:
        subd_summary = '<dict with {:d} entries>'.format(len(subd))
        k_width = max(width - len(subd_summary) - 3, 10)
        if len(k) > k_width:
            k_str = k[:k_width - 1] + ellipsis
        else:
            k_str = k
        print('{:s}{:s} : {:s}'.format(' ' * indent, k_str, subd_summary))
        print_dict(subd, indent = indent + 2)
