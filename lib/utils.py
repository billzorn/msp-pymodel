# handy things

import shutil
import re

unprintable_re = re.compile(r'[^0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~ ]')

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
    
