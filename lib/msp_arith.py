# msp430 shared arithmetic logic

def howmanybits(fields):
    bw = fields['bw']
    if bw == 0:
        return 16
    elif bw == 1:
        return 8
    else:
        raise ValueError('invalid bw: {:s}'.format(repr(bw)))

def trunc_bits(x, bits):
    return x & ~(-1 << bits)

def sxt_bits(x, bits, extbits):
    if src & (1 << (bits - 1)) == 0:
        return trunc_bits(x, bits)
    else:
        return trunc_bits(x | (-1 << bits), extbits)

def twocomp(x, bits):
    if i & (1 << (bits - 1)) == 0:
        return i
    else:
        return i - (1 << bits)    

sr_fieldnames = ['c','z','n','gie','cpuoff','oscoff','scg0','scg1','v']
def unpack_sr(sr):
    sr_fields = {}
    sr_v = sr
    for f in sr_fieldnames:
        sr_fields[f] = sr_v & 1
        sr_v = sr_v >> 1
    sr_fields['reserved'] = sr_v
    return sr_fields

def pack_sr(sr_fields):
    sr_v = 0
    i = 0
    for f in sr_fieldnames:
        sr_v |= sr_fields[f] << i
        i += 1
    sr_v |= sr_fields['reserved']
    return sr_v

# needs a truncated result
def nbit(result_t, bits):
    if twocomp(result_t, bits) < 0:
        return 1
    else:
        return 0

# needs a truncated result
def zbit(result_t):
    if result_t == 0:
        return 1
    else:
        return 0

# needs an untruncated result
def cbit(result, bits):
    mask = (1) << bits
    if result & mask != 0:
        return 1
    else:
        return 0

# all vbit checks need a truncated result
def vbit_add(src, dst, result_t, bits):
    src_signed = twocomp(src, bits)
    dst_signed = twocomp(dst, bits)
    result_signed = twocomp(result_t, bits)
    if ((src_signed >= 0 and dst_signed >= 0 and result_signed < 0)
        or (src_signed < 0 and dst_signed < 0 and result_signed >= 0)):
        return 1
    else:
        return 0

def vbit_sub(src, dst, result_t, bits):
    src_signed = twocomp(src, bits)
    dst_signed = twocomp(dst, bits)
    result_signed = twocomp(result_t, bits)
    if ((src_signed < 0 and dst_signed >= 0 and result_signed < 0)
        or (src_signed >= 0 and dst_signed < 0 and result_signed >= 0)):
        return 1
    else:
        return 0

def vbit_xor(src, dst, result_t, bits):
    src_signed = twocomp(src, bits)
    dst_signed = twocomp(dst, bits)
    if src_signed < 0 and dst_signed < 0:
        return 1
    else:
        return 0

# arith_fn(src, dst, sr_fields)
# vbit_fn(src, dst, result_t, bits)
def execute_arith(fields, arith_fn, vbit_fn, 
                  write_dst = True, alt_cbit = False, clr_vbit = False):
    bits = howmanybits(fields)
    src = trunc_bits(fields['src'], bits)
    dst = trunc_bits(fields['dst'], bits)
    sr_fields = unpack_sr(fields['sr'])
    assert(fields['sr'] == pack_sr(sr_fields)) #TODO
    result = arith_fn(src, dst, sr_fields)
    result_t = trunc_bits(result, bits)
    sr_fields['n'] = nbit(result_t, bits)
    sr_fields['z'] = zbit(result_t)
    if alt_cbit:
        sr_fields['c'] = (1 if sr_fields['z'] == 0 else 0)
    else:
        sr_fields['c'] = cbit(result, bits)
    if clr_vbit:
        sr_fields['v'] = 0
    else:
        sr_fields['v'] = vbit_fn(src, dst, result_t, bits)
    if write_dst:
        fields['dst'] = result_t
    fields['sr'] = pack_sr(sr_fields)
    return

# BCD math
# operation is undefined for poorly encoded numbers; can be determined with experiment
# additionally, the vbit is set to undefined
# more experimentation is required to figure out what happens
def from_bcd(x, bits):
    assert(bits % 4 == 0)
    v = 0
    for i in xrange(0, bits, 4):
        v += ((x >> i) & 0xf) * 10
    return v

def to_bcd(x, bits):
    assert(bits % 4 == 0)
    v = 0
    for i in xrange(0, bits / 4):
        v |= ((x / (10**i)) % 10) << (i * 4)
    return v

def mk_bcd_add(bits):
    def bcd_add(x, y):
        return from_bcd(to_bcd(x, bits) + to_bcd(y, bits), bits)
    return bcd_add

# arith_fn(src, sr_fields)
def execute_shift(fields, arith_fn):
    bits = howmanybits(fields)
    src = trunc_bits(fields['src'])
    sr_fields = unpack_sr(fields['sr'])
    result_t = arith_fn(src, sr_fields)
    sr_fields['n'] = nbit(result_t, bits)
    sr_fields['z'] = zbit(result_t)
    sr_fields['c'] = src & 1
    sr_fields['v'] = 0
    fields['src'] = result_t
    fields['sr'] = pack_sr(sr_fields)
    return
