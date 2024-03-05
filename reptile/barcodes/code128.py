import io
import re
from textwrap import wrap

from reptile.core.units import mm

SET_A = 0
SET_B = 1
SET_C = 2

SHIFT = 98
START_A = 103
START_B = 104
START_C = 105
MODULO = 103
STOP = 106
FNC1 = 207

SET_BY_CODE = {
    START_A: SET_A,
    START_B: SET_B,
    START_C: SET_C,
}

SWAP = {
    101: SET_A,
    100: SET_B,
    99: SET_C,
}

TO_A = 101
TO_B = 100
TO_C = 99

CODE = [
    212222, 222122, 222221, 121223, 121322, 131222, 122213, 122312, 132212, 221213, 221312, 231212, 112232,
    122132, 122231, 113222, 123122, 123221, 223211, 221132, 221231, 213212, 223112, 312131, 311222, 321122,
    321221, 312212, 322112, 322211, 212123, 212321, 232121, 111323, 131123, 131321, 112313, 132113, 132311,
    211313, 231113, 231311, 112133, 112331, 132131, 113123, 113321, 133121, 313121, 211331, 231131, 213113,
    213311, 213131, 311123, 311321, 331121, 312113, 312311, 332111, 314111, 221411, 431111, 111224, 111422,
    121124, 121421, 141122, 141221, 112214, 112412, 122114, 122411, 142112, 142211, 241211, 221114, 413111,
    241112, 134111, 111242, 121142, 121241, 114212, 124112, 124211, 411212, 421112, 421211, 212141, 214121,
    412121, 111143, 111341, 131141, 114113, 114311, 411113, 411311, 113141, 114131, 311141, 411131, 211412,
    211214, 211232, 2331112,
]

CODE128A = re.compile(r"[\x00-\x5F\xC8-\xCF]*")
CODE128B = re.compile(r"[\x20-\x7F\xC8-\xCF]*")
CODE128C = re.compile(r"(\xCF*[0-9]{2}\xCF*)*")
UNTIL_C = re.compile(r"\d{4}")


def encode(data: str):
    pos = 0
    length = len(data)
    lst = []
    c = None
    s = None
    while data:
        if (s := CODE128C.match(data)) and (s := s[0]) and (c is None or len(s) >= 4):
            lst.append(START_C if c is None else TO_C)
            c = CODE128C
            lst.extend(int(b) for b in wrap(s, 2))
        elif (s := CODE128B.match(data)) and (s := s[0]):
            lst.append(START_B if c is None else TO_B)
            c = CODE128B
            if sc := UNTIL_C.search(s):
                s = s[:sc.regs[0][0]]
            lst.extend(ord(b) - 32 for b in s)
        elif (s := CODE128A.match(data)) and (s := s[0]):
            lst.append(START_A if c is None else TO_A)
            c = CODE128A
            if sc := UNTIL_C.search(s):
                s = s[:sc.regs[0][0]]
            lst.extend(o + 64 if (o := ord(b)) < 32 else o - 32 for b in s)
        else:
            raise ValueError(f"Invalid char at position: {pos}")
        data = data[len(s):]
    return lst


def get_barcode(s: str) -> str:
    data = encode(s)
    checksum = sum((i or 1) * c for i, c in enumerate(data)) % 103
    return ''.join(str(i) for i in ([CODE[c] for c in data] + [CODE[checksum], CODE[STOP]]))


def get_png(barcode: str, thickness=3, width: int = None, height: int = 150) -> bytes:
    from PIL import Image, ImageDraw

    barcode = [int(c) * 3 for c in barcode]
    lw = 1
    stream = io.BytesIO()
    if width is None:
        width = sum(barcode) * lw
    # width += 20
    img = Image.new('1', (int(width), int(height)), 1)
    draw = ImageDraw.Draw(img)

    x = 0
    y = 0
    d = True
    for c in barcode:
        if d:
            draw.rectangle(((x, y), (x + c - 1, height - y)), fill=0)
        x += c
        d = not d
    img.save(stream, format='PNG')
    return stream.getvalue()
