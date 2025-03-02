from typing import Optional, List, TYPE_CHECKING
import logging

from jinja2 import Template

from reptile import EnvironmentSettings
from reptile.core import (
    ReportObject, Font, Border, DisplayFormat, Highlight,
)
from reptile.runtime import PreparedText
from reptile.data import DataSource
from .bands import TAG_REGISTRY

logger = logging.getLogger('reptile')


class BandObject(ReportObject):
    left: float = None
    top: float = None
    height: float = None
    width: float = None
    parent: 'Band' = None

    def process(self, context: dict):
        pass

    def prepare(self, stream: List, context):
        obj = self.process(context)
        if obj is not None:
            stream.append(obj)
        return obj

    def load(self, structure: dict):
        self.name = structure['name']
        self.left = structure.get('x', structure.get('left'))
        self.top = structure.get('y', structure.get('top'))
        self.height = structure.get('height')
        self.width = structure.get('width')


class Text(BandObject):
    tag_name = 'text'
    _field: str = None
    _template: Template = None
    _context: dict = None
    background: str = None
    color: int = None
    auto_size = False
    can_grow = False
    can_shrink = False
    font: Font = None
    halign: str = None
    valign: str = None
    border: Border = None
    word_wrap = False
    qrcode: bool = False
    top = 0
    left = 0
    width = 120
    height = 20
    allow_tags: bool = False
    allow_expressions: bool = True
    brush_style = None
    # datasource: DataSource = None
    text: Optional[str] = None
    display_format: DisplayFormat = None
    calc_size = None

    def __init__(self, text: str = None):
        super().__init__()
        self.font = Font()
        self.border = Border()
        self.text = text

    def load(self, structure: dict):
        super().load(structure)
        self.text = structure.get('text')
        if 'font' in structure:
            f = structure['font']
            self.font = Font()
            self.font.name = f.get('name')
            size = f.get('size')
            if size:
                if isinstance(size, str):
                    self.font.size = int(''.join(filter(lambda c: c.isdigit(), size)))
                else:
                    self.font.size = size
            if f.get('bold'):
                self.font.bold = True
            if f.get('italic'):
                self.font.italic = True
            if f.get('underline'):
                self.font.underline = True
            if color := f.get('color'):
                self.font.color = color
        valign = structure.get('vAlign')
        halign = structure.get('hAlign')
        self.can_grow = structure.get('canGrow')
        self.word_wrap = structure.get('wrap', False)
        self.qrcode = structure.get('qrCode', False)

        if valign == 1:
            self.valign = 'center'
        elif valign == 2:
            self.valign = 'bottom'
        if halign == 1:
            self.halign = 'center'
        elif halign == 2:
            self.halign = 'right'

        border = structure.get('border')
        if border:
            self.border.width = border.get('width', 0.5)
            self.border.style = border.get('style', 1)
            if border.get('all'):
                self.border.bottom = self.border.left = self.border.top = self.border.right = True
            else:
                if border.get('top'):
                    self.border.top = True
                if border.get('right'):
                    self.border.right = True
                if border.get('bottom'):
                    self.border.bottom = True
                if border.get('left'):
                    self.border.left = True

        bg = structure.get('background')
        if bg:
            self.background = bg.get('color')

        disp_fmt = structure.get('displayFormat')
        if disp_fmt:
            self.display_format = DisplayFormat(disp_fmt['format'], disp_fmt['type'])
        highlight = structure.get('highlights')
        if highlight:
            self.highlight = Highlight(highlight[0])
        else:
            self.highlight = Highlight(structure.get('highlight'))

    highlight: Highlight = None

    @property
    def field(self):
        return self._field

    @field.setter
    def field(self, value):
        self._field = value
        self.text = None

    @property
    def template(self):
        if self._template is None:
            self._template = EnvironmentSettings.env.from_string(self.text, {'this': self})
        return self._template

    def template2(self, text: str):
        return Template(text, variable_start_string='${', variable_end_string='}')

    def process(self, context, level=3) -> PreparedText:
        new_obj = PreparedText()
        new_obj.height = self.height
        new_obj.width = self.width
        new_obj.left = self.left
        new_obj.top = self.top
        new_obj.allow_tags = self.allow_tags
        if self.allow_expressions:
            try:
                new_obj.text = self.template.render(**context)
                if '${' in new_obj.text:
                    context['report']._pending_objects.append((self.template2(new_obj.text), new_obj))
            except Exception as e:
                logger.error(f"Error evaluating object: {self.name or ''}")
                logger.exception(e)
                new_obj.text = EnvironmentSettings.error_text
                new_obj.error = True
        else:
            new_obj.text = self.text
        new_obj.font_name = self.font.name
        if self.font.size:
            new_obj.font_size = self.font.size
        if self.font.color:
            new_obj.color = self.font.color
        new_obj.font_bold = self.font.bold
        new_obj.font_italic = self.font.italic
        new_obj.background = self.background
        new_obj.brush_style = self.brush_style
        if self.highlight and self.highlight.eval_condition(context):
            new_obj.brush_style = self.highlight.brush_style
            new_obj.background = self.highlight.background or '#ffffff'
        new_obj.valign = self.valign
        new_obj.halign = self.halign
        new_obj.border = self.border
        new_obj.wrap = self.word_wrap
        new_obj.qrcode = self.qrcode
        new_obj.can_grow = self.can_grow
        if (self.can_grow or self.can_shrink) and level > 1 and self.calc_size:
            w, h = self.calc_size(new_obj)
            if self.can_shrink:
                new_obj.can_shrink = True
                h = min(new_obj.height, h)
            if self.can_grow:
                new_obj.can_grow = True
                h = max(new_obj.height, h)
            new_obj.height = h
        return new_obj


class SysText(Text):
    pass


class Image(BandObject):
    element_type = 'image'
    filename: str = None
    url: str = None
    picture: bytes = None
    _datasource: DataSource = None
    field: str = None
    size_mode = None

    def prepare(self, stream: List, context):
        from reptile.runtime import PreparedImage
        img = PreparedImage()
        img.left = self.left
        img.top = self.top
        img.height = self.height
        img.width = self.width
        img.size_mode = self.size_mode
        if self.field:
            if self._datasource:
                img.picture = context[self.datasource.name][self.field]
            else:
                try:
                    img.picture = self.parent.page.report.variables[self.field]
                except KeyError:
                    print('Image not found for field', self.field)
        else:
            img.picture = self.picture
        stream.append(img)

    @property
    def datasource(self):
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        if isinstance(value, str):
            value = self.parent.page.report.get_datasource(value)
        self._datasource = value

    def load(self, structure: dict):
        from reptile.runtime import SizeMode
        super().load(structure)
        self.field = structure.get('field')
        size_mode = structure.get('sizeMode')
        if size_mode == 'center':
            self.size_mode = SizeMode.CENTER
        elif size_mode == 'zoom':
            self.size_mode = SizeMode.ZOOM
        elif size_mode == 'stretch':
            self.size_mode = SizeMode.STRETCH
        else:
            self.size_mode = SizeMode.NORMAL


class Line(BandObject):
    size = 0

    def __init__(self, band):
        self.border = Border()

    def prepare(self, stream: List, context):
        from reptile.runtime import PreparedLine
        line = PreparedLine()
        line.left = self.left
        line.top = self.top
        line.width = self.width
        line.height = self.height
        line.size = self.size
        stream.append(line)


class TableColumn:
    def __init__(self, table):
        self.table = table
        self.name = None
        self.width = 0


class TableCell(Text):
    def __init__(self, band):
        super().__init__(band)


class TableRow:
    def __init__(self, table):
        self.table = table
        self.name = None
        self.height = 0
        self.cells = []

    def add_cell(self, cell):
        self.cells.append(cell)


class Table(BandObject):
    def __init__(self, band):
        self.columns = []
        self.rows = []

    def prepare(self, stream: List, context):
        y = self.top
        h = 0
        row_count = len(self.rows)
        col_count = len(self.columns)
        for ay, row in enumerate(self.rows):
            x = self.left
            for ax, cell in enumerate(row.cells):
                cell.top = y
                cell.left = x
                cell.height += 4
                cell.prepare(stream, context)
                x = cell.left + cell.width
            h += row.height + 4
            y = self.top + h
        self.height = y

    def add_column(self, column):
        self.columns.append(column)

    def add_row(self, row):
        self.rows.append(row)


TAG_REGISTRY['text'] = Text
TAG_REGISTRY['Text'] = Text
TAG_REGISTRY['image'] = Image
TAG_REGISTRY['Image'] = Image
