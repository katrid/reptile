import enum
from typing import List, Type, Optional
from dataclasses import dataclass


@dataclass(slots=True, init=True)
class ReportObject:
    x: int = None
    y: int = None
    width: int = None
    height: int = None


class Border(enum.IntFlag):
    top = 1
    right = 2
    bottom = 4
    left = 8


class PreparedObject:
    def __init__(self):
        self.x: Optional[float] = None
        self.y: Optional[float] = None


class PreparedText(PreparedObject):
    __slots__ = (
        'left', 'top', 'height', 'width', 'allow_tags', 'text', 'font_name', 'font_size', 'font_bold', 'font_italic',
        'background', 'brush_style', 'valign', 'halign', 'border', 'wrap', 'can_grow', 'error', 'color', 'can_grow',
        'padding',
    )

    def __init__(self, text=None, x=0, y=0):
        self.text = text
        self.left = x
        self.top = y
        self.width = None
        self.height = 0
        self.font_bold = False
        self.font_italic = False
        self.font_name = 'Helvetica'
        self.font_size = 9
        self.padding = None
        self.background = None
        self.wrap = False
        self.error = False
        self.color = '#000000'
        self.can_grow = False

    def dump(self):
        return {
            'left': self.left,
            'top': self.top,
            'height': self.height,
            'width': self.width,
            'text': self.text,
            'fontSize': self.font_size,
            'fontName': self.font_name,
            'error': self.error,
        }


class SizeMode(enum.IntEnum):
    NORMAL = 0
    CENTER = 1
    AUTO = 2
    ZOOM = 3
    STRETCH = 4


class PreparedImage:
    __slots__ = ('picture', 'left', 'top', 'height', 'width', 'size_mode')

    def __init__(self):
        self.size_mode = SizeMode.NORMAL
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.picture = None


class PreparedLine:
    __slots__ = ('left', 'top', 'height', 'width', 'direction', 'line_width', 'color', 'line_style')

    def __init__(self):
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.line_width = 1
        self.direction = 0
        self.color = 0
        self.line_style = 0


class Heading(PreparedText):
    def __init__(self, level, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.level = level


class Cell(PreparedText):
    def __init__(self, value, x: Optional[int] = None, y: Optional[int] = None, fmt=None):
        super().__init__()
        self.value = value
        self.format = fmt

    def __str__(self):
        return str(self.value)

    def as_text(self):
        return str(self)


class Container:
    pass


@dataclass
class PreparedBand:
    left: int = None
    top: int = None
    width: int = None
    height: int = None
    bottom: int = 0
    band_type = None
    objects: list[PreparedObject] = None
    fill = None

    def set_page(self, page: 'PreparedPage'):
        self.top = page.y
        self.bottom = self.top + self.height

    def dump(self):
        return {
            'objects': [obj.dump() for obj in self.objects],
            'left': self.left,
            'top': self.top,
            'height': self.height,
            'width': self.width,
        }


class Line(Container):
    cell_class: Type[Cell] = Cell
    cells: List[Cell] = None

    def __init__(self):
        self._prepare()

    def _prepare(self):
        self.cells = []

    def write(self, *args):
        for arg in args:
            self.cells.append(self.cell_class(arg))

    def __getitem__(self, item):
        return self.cells[item]


class PreparedPage:
    __slots__ = ('height', 'width', 'bands', 'index', 'margin', 'x', 'y', 'ay', 'watermark')

    def __init__(self, height, width, margin=None):
        self.height = height
        self.width = width
        if margin:
            self.y = margin.top
            self.ay = height - margin.bottom
            self.x = margin.left
        self.bands: List[PreparedBand] = []
        self.margin = margin
        self.watermark = None

    def add_band(self, left, top, width, height):
        band = PreparedBand(left, top, width, height)
        self.bands.append(band)
        return band

    def dump(self) -> dict:
        return {
            'bands': [b.dump() for b in self.bands]
        }

    def new_line(self):
        self._line = Line()
        self.lines.append(self._line)
        return self._line

    @property
    def line(self):
        if self._line is None:
            self.new_line()
        return self._line

    def heading(self, title: str, level=1):
        h = Heading(level)
        h.text = title
        self.lines.append(h)

    def table(self, data=None):
        from .table import Table
        table = Table()
        self.lines.append(table)
        return table

    def dump(self) -> dict:
        return {
            'bands': [b.dump() for b in self.bands]
        }


class ReportStream:
    _page: PreparedPage = None

    def __init__(self, report):
        self.report = report
        self.pages: List[PreparedPage] = []

    def add_line(self, line):
        self.page.lines.append(line)

    def new_line(self):
        return self.page.new_line()

    def new_page(self):
        self._page = PreparedPage(self)
        self.pages.append(self._page)
        return self._page

    def heading(self, title: str, level=1):
        self.page.heading(title, level)

    def write(self, *args):
        self.line.write(*args)

    @property
    def line(self):
        return self.page.line

    @property
    def page(self):
        if self._page is None:
            self.new_page()
        return self._page

    def dump(self) -> dict:
        """
        Dump prepared report to dict
        :return:
        """
        return {
            'pages': [p.dump() for p in self.pages],
            'level': self.report._level,
        }


class PreparedBarcode:
    __slots__ = ('barcode', 'data', 'left', 'top', 'height', 'width', 'size_mode', 'thickness')
    data: bytes
    barcode: str
    thickness: float

    def __init__(self):
        self.size_mode = SizeMode.NORMAL
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.thickness = 3
