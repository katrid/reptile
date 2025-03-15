from typing import Optional
import enum
import re

from jinja2 import Template

from reptile import EnvironmentSettings
from .units import mm

ERROR_TEXT = '-'


class Font:
    __slots__ = ('name', 'size', 'bold', 'italic', 'underline', 'color')

    def __init__(self):
        self.name = None
        self.size = None
        self.italic = False
        self.bold = False
        self.underline = False
        self.color = 0

    def __bool__(self):
        return bool(self.name)

    def dump(self) -> dict | None:
        if self:
            res = {
                'name': self.name,
            }
            if self.size:
                res['size'] = self.size
            if self.bold:
                res['bold'] = self.bold
            if self.italic:
                res['italic'] = self.italic
            if self.underline:
                res['underline'] = self.underline
            if self.color:
                res['color'] = self.color
            return res


class VAlign(enum.IntEnum):
    TOP = 0
    CENTER = 1
    BOTTOM = 2


class HAlign(enum.IntEnum):
    LEFT = 0
    CENTER = 1
    RIGHT = 2
    JUSTIFY = 3


class Border:
    __slots__ = ('left', 'top', 'right', 'bottom', 'width', 'color', 'style')

    def __init__(self):
        self.left: bool = False
        self.top: bool = False
        self.right: bool = False
        self.bottom: bool = False
        self.width = 1
        self.color: int = 0x000000
        self.style: Optional[int] = None

    def __bool__(self):
        return self.left or self.top or self.right or self.bottom

    def dump(self) -> dict | None:
        if self:
            return {
                'left': self.left,
                'top': self.top,
                'right': self.right,
                'bottom': self.bottom,
                'width': self.width,
                'color': self.color,
                'style': self.style,
            }


class ReportObject:
    tag_name: str = None
    name: str = None


_re_number_fmt = re.compile(r'\.(\d)f')


class DisplayFormat:
    __slots__ = ('format', 'kind', 'decimal_pos')

    def __init__(self, format: str = None, kind: str = None):
        self.format: str = format
        self.kind: str = kind
        self.decimal_pos = None

    def load(self, data: dict):
        self.format = data['format']
        self.kind = data.get('kind', data.get('type'))
        self.decimal_pos = data.get('decimal_pos')

    def update_format(self):
        if self.kind == 'Numeric':
            self.decimal_pos = _re_number_fmt.match(self.format)

    def dump(self) -> dict:
        return {
            'format': self.format,
            'kind': self.kind,
        }


class Highlight:
    font_name = ''
    font_size: int = None
    color: int = None
    condition: str = None
    fill_type = ''
    brush_style = 0
    background: int = None
    _template: Template = None

    def __init__(self, structure: dict = None):
        if structure:
            self.condition = structure['condition']
            font = structure.get('font')
            if font:
                self.font_name = font.get('name')
                self.font_size = font.get('size')
            background = structure.get('background')
            if background:
                self.background = background.get('color')

    def eval_condition(self, context):
        if self._template is None:
            self._template = EnvironmentSettings.env.from_string('{{%s}}' % self.condition)
        return self._template.render(**context).strip() == 'True'


class Padding:
    __slots__ = ('left', 'top', 'right', 'bottom')

    def __init__(self, left=0, top=0, right=0, bottom=0):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __bool__(self):
        return bool(self.left or self.top or self.right or self.bottom)

    def dump(self) -> dict | None:
        if self:
            return {
                'left': self.left,
                'top': self.top,
                'right': self.right,
                'bottom': self.bottom,
            }


class Margin:
    __slots__ = ('left', 'top', 'right', 'bottom')

    def __init__(self, left=5, top=5, right=5, bottom=5):
        self.left = left * mm
        self.top = top * mm
        self.right = right * mm
        self.bottom = bottom * mm


class BasePage(ReportObject):
    pass
