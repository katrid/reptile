from typing import Optional
import re

from jinja2 import Template

from reptile import EnvironmentSettings
from .units import mm


ERROR_TEXT = '-'


class Font:
    __slots__ = ('name', 'size', 'bold', 'italic', 'underline')

    def __init__(self):
        self.name: Optional[str] = None
        self.size: Optional[int] = None
        self.italic = False
        self.bold = False
        self.underline = False

    def __bool__(self):
        return bool(self.name)


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


class ReportObject:
    tag_name: str = None
    name: str = None


_re_number_fmt = re.compile(r'\.(\d)f')


class DisplayFormat:
    __slots__ = ('format', 'kind', 'decimal_pos')

    def __init__(self, format: str, kind: str):
        self.format: str = format
        self.kind: str = kind

    def update_format(self):
        if self.kind == 'Numeric':
            self.decimal_pos = _re_number_fmt.match(self.format)


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


class Margin:
    __slots__ = ('left', 'top', 'right', 'bottom')

    def __init__(self, left=5, top=5, right=5, bottom=5):
        self.left = left * mm
        self.top = top * mm
        self.right = right * mm
        self.bottom = bottom * mm


class BasePage(ReportObject):
    pass


