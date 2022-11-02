from io import StringIO, IOBase
from typing import Optional


class Object:
    def write(self, file: 'FileBuffer'):
        pass


class IndirectObject(Object):
    def __init__(self, id=None, gen=0, value=None):
        self.id = id
        self.generation = gen
        self.value = value
        self.ref = f'{id} {gen} R'


class String(Object):
    pass


class Boolean(Object):
    pass


class Numeric(Object):
    pass


class Name(Object):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return '/' + self.name


class Array(Object):
    def __str__(self):
        return f"[ {' '.join(self)} ]"


class Dictionary(Object):
    def __init__(self, **kwargs):
        self._dict = dict(kwargs)

    def __str__(self):
        return f"<<\n{' '.join(f'{k} {_TYPE_MAP.get(v.__class__, v.__class__).__str__(v)}' for k, v in self.items())}\n>>\n"


class Stream(Object):
    def __str__(self):
        return f'<< /Length {len(self)} >>\nstream\n{self}endstream\n'


class Resources(Dictionary):
    def __init__(self):
        self.font = Dictionary()
        super().__init__(Font=self.font)


class Page:
    def __init__(self):
        self.contents = []


class XRef:
    def __init__(self, pos: int):
        self.pos = pos

    def begin(self, file):
        file.buffer.write('xref\n')


class Fonts(IndirectObject):
    def __init__(self):
        super().__init__()
        self._fonts_count = 0
        self.fonts = {}
        self.names = {}

    def __str__(self):
        return f"<<\n{' '.join(f'{name} {key} 0 R' for name, key in zip(self.names.values(), self.fonts.values()))}\n>>\n"


class ByRef:
    def __init__(self, obj: IndirectObject):
        self.obj = obj

    def __str__(self):
        return f'{self.obj.id} 0 R'


_TYPE_MAP = {
    dict: Dictionary,
    list: Array,
    int: Numeric,
}


class Document:
    root: IndirectObject = None  # root catalog
    base_font = 'Helvetica'
    title: str = None
    subject: str = None
    author: str = 'anonymous'
    creator: str = 'Reptile'
    _id = 0

    def __init__(self):
        self.page_count = 0
        self.objects = []
        self.buffer = StringIO()
        self.fonts = Fonts()
        self._fonts_ref = {}
        self._font = None
        self._leading = None
        self._text_mode = None
        self.char_spacing = None
        self.word_spacing = None
        self.page_width = 612
        self.page_height = 792
        self.pages = []
        self.xref = {}
        self._contents = StringIO()
        self.page = None
        self.version = '1.7'
        self.resources = {}
        self._proc_set = ['/PDF', '/Text']
        self._res_fonts = {}  # fonts dict
        self.begin()
        self.resources = {'/ProcSet': self._proc_set, '/Font': self.fonts}
        self.set_font('Helvetica')

    def get_id(self):
        self._id += 1
        return self._id

    def begin(self):
        self.buffer.write('%PDF-' + self.version + '\n% Reptile Generated PDF\n')

    def write_info(self):
        info = {}
        if self.title:
            info['/Title'] = f'({self.title})'
        if self.author:
            info['/Author'] = f'({self.author})'
        if self.creator:
            info['/Creator'] = f'({self.creator})'
        return self.write_object(info)

    def write_catalog(self, pages):
        self.write_object({})
        # self.root = self.write_object(Dictionary(Type='Catalog', Pages=pages))

    def write_object(self, obj, _id=None):
        if isinstance(obj, IndirectObject):
            if obj.id is None:
                self._id += 1
                _id = obj.id = self._id
        else:
            if _id is None:
                self._id += 1
                _id = self._id
        # new_obj = IndirectObject(self.id(), 0, value=obj)
        self.xref[_id] = self.buffer.tell()
        # new_obj.write(self.buffer)
        # self.buffer.write(str(new_obj))
        self.buffer.write(f'{_id} 0 obj\n')
        if isinstance(obj, dict):
            self.buffer.write(Dictionary.__str__(obj))
        elif isinstance(obj, StringIO):
            self.buffer.write(Stream.__str__(obj.getvalue()))
        else:
            self.buffer.write(str(obj))
        self.buffer.write('endobj\n')
        return self._id

    def trailer(self):
        self.buffer.write('trailer\n')
        self.buffer.write('<<')
        self.buffer.write('/Root ')
        self.buffer.write(f'/Info {self.root.ref}')

    def set_font(self, font: str, size=9, leading=None):
        if font not in self.fonts.fonts:
            fref = self.add_font(font)
        else:
            fref = self.fonts.names[font]
        # if leading is None:
        #     leading = size * 1.2
        self._leading = leading
        self._font = f'{fref} {size}'
        # self._contents.write(f'BT {self._font} Tf {leading} TL ET\n')

    def text(self, text: str, x=100, y=100):
        # begin
        self._contents.write(f'BT {self._font} Tf\n')
        if self._leading:
            self._contents.write(f'{self._leading} TL\n')
        if self.char_spacing is not None:
            self._contents.write(f'{self.char_spacing} Tc')
        if self.word_spacing is not None:
            self._contents.write(f'{self.word_spacing} Tw')
        if self._text_mode is not None:
            self._contents.write(f'{self._text_mode} Tr')
        self._contents.write(f'{x} {y} Td\n')
        self._contents.write(f'({text}) Tj\n')
        self._contents.write('ET\n')

    def add_font(self, font: str):
        # self.fonts[font] = self.write_object(Dictionary(Type='Font', Subtype='Type1', BaseFont=font))
        self.fonts._fonts_count += 1
        fid = self.fonts.fonts[font] = self.write_object({
            '/Type': '/Font', '/Subtype': '/Type1', '/BaseFont': f'/{font}',
            '/Name': f'/F{self.fonts._fonts_count}',
            '/Encoding': '/WinAnsiEncoding',
        })
        fref = self.fonts.names[font] = f'/F{self.fonts._fonts_count}'
        return fref

    def _end_page(self, page):
        _id = self.write_object(self._contents)
        page['/Contents'] = f'{_id} 0 R'
        if page:
            self.pages.append(page)
        self.page = None

    def new_page(self, width=None, height=None):
        if self.page:
            self._end_page(self.page)
        self._contents = StringIO()
        self.resources = {'/ProcSet': self._proc_set, '/Font': ByRef(self.fonts)}
        self.page_count += 1
        self.page = {
            '/Type': '/Page', '/Resources': self.resources,
            '/MediaBox': f'[0 0 {width or self.page_width}.0000 {height or self.page_height}.0000]'
        }

    def end(self):
        self.write_object(self.fonts)
        if self.page:
            self._end_page(self.page)
        parent_id = self.get_id()
        kids = []
        for p in self.pages:
            p['/Parent'] = f'{parent_id} 0 R'
            kids.append(f'{self.write_object(p)} 0 R')
        if self.page:
            self._end_page(self.page)

        pages = self.write_object({
            '/Type': '/Pages', '/Kids': kids, '/Count': self.page_count,
        }, parent_id)
        info_id = self.write_info()
        catalog_id = self.write_object({'/Type': '/Catalog', '/Pages': f'{parent_id} 0 R'})
        offset = self.buffer.tell()
        # xref
        self._id += 1
        self.buffer.write(f'xref\n0 {self._id}\n0000000000 65535 f\n')
        for i in range(self._id - 1):
            self.buffer.write(f'{str(self.xref[i + 1]).zfill(10)} 00000 n\n')
        # trailer
        self.buffer.write('trailer\n<<\n')
        self.buffer.write(f'/Info {info_id} 0 R\n')
        self.buffer.write(f'/Root {catalog_id} 0 R\n')
        self.buffer.write(f'/Size {self._id}\n')
        self.buffer.write(f'>>\nstartxref\n{offset}\n%%EOF')

    def save(self, filename: str):
        self.end()
        from shutil import copyfileobj
        with open(filename, 'w') as f:
            self.buffer.seek(0)
            copyfileobj(self.buffer, f)


class FileBuffer:
    root: IndirectObject = None

    def __init__(self, version='1.7'):
        self.version = version
        self.buffer = StringIO()
        self.objects = []

    def begin(self):
        self.buffer.write('%PDF' + self.version + '\n')
        # self.buffer.write('%PDF' + self.version + '\n.\n%\223\214\213\236 Reptile Generated PDF\n')

    def end(self):
        self.buffer.write('\n%%EOF')
