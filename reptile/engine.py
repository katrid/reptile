from typing import List, Optional, Iterable, TYPE_CHECKING
from functools import partial
from itertools import groupby
from enum import Enum
from decimal import Decimal
import datetime
import re
import sqlparse
from jinja2 import Template, Environment, pass_context
from jinja2 import contextfunction
if TYPE_CHECKING:
    from .totals import Total
from .runtime import PreparedBand, PreparedText, PreparedPage, PreparedImage

from .units import mm


class FormatSettings:
    numeric_format: str = '%.2f'
    date_format: str = None
    datetime_format: str = None


class ReportEngine:
    env = None

    @classmethod
    def create_template_env(cls):
        if cls.env:
            return cls.env
        env = Environment()
        env.globals['str'] = str
        env.globals['sum'] = sum
        # env.globals['total'] = total
        # env.globals['avg'] = avg
        env.globals['count'] = len
        if cls.env is None:
            cls.env = env
        return env


@pass_context
def finalize(context, val):
    this = context.parent.get('this')
    if val and isinstance(this, Text):
        if disp := this.display_format:
            if isinstance(val, (Decimal, float)) and disp.kind == 'Numeric':
                return f'{{:{disp.format}}}'.format(val)
            if isinstance(val, (datetime.date, datetime.datetime)) and disp.kind == 'DateTime':
                return val.strftime(disp.format)
    if val is None:
        return ''
    if isinstance(val, Decimal):
        return '%.2f' % val
    if isinstance(val, float):
        return '%.2f' % val
    return val


report_env = Environment(finalize=finalize)
report_env.globals['str'] = str
report_env.globals['sum'] = sum
# env.globals['total'] = total
# env.globals['avg'] = avg
report_env.globals['count'] = len


def COUNT(obj):
    return obj.get_count()


def SUM(expr, band=None, flag=None):
    return sum(expr)


def AVG(expr, band=None, flag=None):
    return sum(expr) / len(expr)


def avg(values):
    return sum(values) / len(values)


@pass_context
def total(context, op, field=None):
    if isinstance(op, str) and field is None:
        field = op
        op = sum
    records = context.parent['records']
    if records:
        rec = records[0]
        if isinstance(rec, dict):
            fn = lambda rec: rec[field] or 0
        else:
            fn = lambda rec: getattr(rec, field) or 0
        return op(list(map(fn, records)))
    return 0


report_env.globals['COUNT'] = COUNT
report_env.globals['SUM'] = SUM
report_env.globals['AVG'] = AVG
report_env.globals['avg'] = avg
report_env.globals['total'] = total


class ReprintError(Exception):
    pass


class Report:
    title: str = None
    page_count = 0
    _pending_objects: List['Text'] = None

    def __init__(self):
        self.pages: List['Page'] = []
        self.datasources: List['DataSource'] = []
        self.totals: List[Total] = []
        self.variables = {}
        self.objects = []
        # default database connection
        self.connection = None
        self._context = None

    def __getitem__(self, item):
        for page in self.pages:
            if page.name == item:
                return page

    def add_page(self, page: 'Page'):
        self.pages.append(page)
        if page.report != self:
            page.report = self

    def new_page(self) -> 'Page':
        return Page(self)

    def prepare(self):
        self.stream = stream = []
        self._pending_objects = []
        self.page_count = 0
        self._context = {
            'page_index': 0,
            'page_count': 0,
            'report': self,
            'date': datetime.date.today(),
            'time': datetime.datetime.now().strftime('%H:%M')
        }
        # detect subreports
        for obj in self.objects:
            if isinstance(obj, SubReport):
                obj.report_page = self[obj.page_name]
        # initialize context with datasource
        for ds in self.datasources:
            if ds.name:
                ds.params.assign(self.variables)
                ds.open()
                if ds.data:
                    self._context[ds.name] = ds.data[0]
                else:
                    self._context[ds.name] = ds.data

        for page in self.pages:
            if not page.subreport:
                page.prepare(stream)

        for txt, obj in self._pending_objects:
            self._context['page_count'] = self.page_count
            obj.text = txt.render(self._context)

        return {
            'pages': stream,
        }

    def get_datasource(self, name):
        for ds in self.datasources:
            if ds.name == name:
                return ds

    def from_string(self, s: str):
        self.read_xml(etree.fromstring(s))

    def load_file(self, filename: str):
        if filename.endswith('.xml'):
            with open(filename, 'rb') as f:
                self.from_string(f.read())

    def register_datasource(self, datasource):
        self.datasources[datasource.name] = datasource


class ReportObject:
    name: str = None
    _report: Report = None

    @property
    def report(self):
        return self._report

    @report.setter
    def report(self, value: Report):
        self.set_report(value)

    def set_report(self, value: Report):
        self._report = value


class Margin:
    __slots__ = ('left', 'top', 'right', 'bottom')

    def __init__(self):
        self.left = 5 * mm
        self.top = 5 * mm
        self.right = 5 * mm
        self.bottom = 5 * mm


class Page(ReportObject):
    _page_header = None
    _page_footer = None
    _report_title = None
    _report: Report = None
    _context: dict = None
    _current_page: PreparedPage = None
    width: float = 0
    height: float = 0
    title_before_header = True
    reset_page_number = False
    stream = None
    subreport: 'SubReport' = None

    def __init__(self, report: Report = None):
        self.callbacks = []
        self.report = report
        self.bands: List['Band'] = []
        self.margin = Margin()

    def add_band(self, band: 'Band'):
        self.bands.append(band)
        if band.page != self:
            band.page = self

    def prepare(self, stream: List):
        self._context = self.report._context
        self.stream = stream
        # detect special bands
        for band in self.bands:
            if isinstance(band, ReportTitle):
                self._report_title = band
            if isinstance(band, PageHeader):
                self._page_header = band
            elif isinstance(band, PageFooter):
                self._page_footer = band

        page = self.new_page(self._context)
        if self._report_title:
            self._report_title.prepare(page, self._context)

        for band in self.bands:
            # Only root bands must be prepared
            if band.parent is None and isinstance(band, (GroupHeader, DataBand)):
                page = band.prepare(page, self._context) or page

        self.end_page(page, self._context)

    def new_page(self, context):
        if self._current_page is not None:
            self.end_page(self._current_page, context)
        page = PreparedPage(self.height, self.width, self.margin)
        self.report.page_count += 1
        page.index = self.report.page_count
        context['page_index'] = page.index
        page.bands = []
        if self._page_header:
            self._page_header.prepare(page, context)
        if self._page_footer:
            page.ay -= self._page_footer.height
        self._current_page = page
        self.report.stream.append(page)
        for cb in self.callbacks:
            cb(page, context)
        return page

    def end_page(self, page: PreparedPage, context):
        if self._page_footer:
            page.ay += self._page_footer.height
            page.y = page.ay - self._page_footer.height
            self._page_footer.prepare(page, context)

    def set_report(self, value: Report):
        if self._report and self in self._report.pages:
            self._report.pages.remove(self)
        self._report = value
        if value:
            value.add_page(self)

    def add_new_page_callback(self, cb):
        self.callbacks.append(cb)

    def remove_new_page_callback(self, cb):
        self.callbacks.remove(cb)


class DataSource(ReportObject):
    _data: Optional[Iterable] = None
    _opened = False
    connection = None

    def __init__(self, name: str, data: Iterable = None):
        self.name: str = name
        self._data = data

    def open(self):
        self._opened = True

    def close(self):
        self._data = None
        self._opened = False

    @property
    def data(self) -> Iterable:
        return self._data

    def set_report(self, value: Report):
        if self._report and self in self._report.pages:
            self._report.datasources.remove(self)
        self._report = value
        if value:
            value.datasources.append(self)


class DataProxy:
    def __init__(self, data: Iterable):
        self.data = data

    def __getattr__(self, item):
        if self.data and isinstance(self.data, list):
            return self.data[0][item]

    def values(self, item):
        return [rec[item] or Decimal(0.00) if isinstance(rec, dict) else getattr(rec, item) for rec in self.data]

    def __iter__(self):
        return iter(self.data)


class Band(ReportObject):
    bg_color: int = None
    height: int = None
    width: int = None
    left: int = None
    top: int = None
    _page: Page = None
    _parent: 'Band' = None
    _context: dict = None
    band_type = 'band'
    auto_height = False
    _x = _y = 0
    _page: PreparedPage = None

    def __init__(self, page: Page):
        self.page = page
        self.report = page.report
        self.objects: List['ReportElement'] = []
        self.children: List['Band'] = []
        self.subreports: List['SubReport'] = []

    def add_band(self, band: 'Band'):
        band.parent = self

    def add_element(self, element: 'ReportElement'):
        if isinstance(element, SubReport):
            self.subreports.append(element)
        else:
            self.objects.append(element)
        if element.band != self:
            element.band = self

    def prepare(self, page: PreparedPage, context):
        page = self.prepare_objects(page, context)
        if self.subreports:
            self.prepare_subreports(page, context)
        return page

    def prepare_objects(self, page: PreparedPage, context):
        context = self._context = context or self.page._context
        band = PreparedBand()
        band.band_type = self.band_type
        objs = band.objects = []
        band.height = self.height
        band.width = self.width
        band.left = page.x
        band.top = page.y
        for obj in self.objects:
            new_obj = obj.prepare(objs, context)
            if new_obj and (new_obj.height + new_obj.top) > band.height:
                band.height = new_obj.height + new_obj.top
        band.bottom = band.top + band.height
        if int(band.bottom) > int(page.ay):
            page = self.page.new_page(context)
            band.setPage(page)
        page.bands.append(band)
        page.y = band.bottom
        # save position
        self._x = band.left
        self._y = band.top
        return page

    def prepare_subreports(self, page: PreparedPage, context):
        x = self._x
        y = self._y
        for sub in self.subreports:
            sub._x = x
            sub._y = y
            sub.prepare(page, context)

    @property
    def page(self):
        return self._page

    @page.setter
    def page(self, value):
        if self._page is not None:
            self._page.bands.remove(self)
        self._page = value
        if value is not None:
            self._page.add_band(self)

    @property
    def parent(self) -> 'Band':
        return self._parent

    @parent.setter
    def parent(self, value: 'Band'):
        if self._parent is not None:
            self._parent.children.remove(self)
        self._parent = value
        if value is not None:
            self.page = value.page
            value.children.append(self)


class PageHeader(Band):
    band_type = 'PageHeader'


class PageFooter(Band):
    band_type = 'PageFooter'


class Footer(Band):
    band_type = 'Footer'

    def __init__(self, page: Page):
        parent_band = page.bands[-1]
        super().__init__(page)
        if isinstance(parent_band, DataBand):
            parent_band.footer = self


class HeaderBand(Band):
    band_type = 'Header'


class ReportSummary(Band):
    band_type = 'ReportSummary'


class ChildBand(Band):
    band_type = 'ChildBand'


class DataBand(Band):
    band_type = 'data'
    _datasource: DataSource = None
    row_count: int = None
    header: 'HeaderBand' = None
    footer: 'Footer' = None
    group_header: 'GroupHeader' = None

    def prepare(self, page: PreparedPage, context):
        data = self.data
        self._context = context
        if data:
            return self.process(data, page, context)

    def process(self, data: Iterable, page: PreparedPage, context: dict):
        context.setdefault('line', 1)

        # print the header band
        if self.header and not self.group_header:
            page = self.header.prepare(page, context)

        self._context = context
        for i, row in enumerate(data):
            row = RecordHelper(row)
            if self.datasource:
                context[self.datasource.name] = row
            context['record'] = row
            context['row'] = i + 1
            context['line'] += 1
            if self.name:
                context[self.name] = self
            even = context['even'] = bool(i % 2)
            context['odd'] = not even
            page = super().prepare(page, context)
        context[self.datasource.name] = DataProxy(self.datasource.data)
        # print the footer band
        if self.footer and not self.group_header:
            page = self.footer.prepare(page, context)
        return page

    @property
    def data(self):
        if self.datasource:
            self.datasource.open()
            return self.datasource.data
        elif self.row_count:
            return range(self.row_count)

    @property
    def datasource(self):
        return self._datasource

    @datasource.setter
    def datasource(self, value: DataSource):
        if isinstance(value, str):
            # get datasource by the name
            value = self.page.report.get_datasource(value)
        self._datasource = value

    def get_count(self):
        return self._context['row']


class Group:
    def __init__(self, grouper, data: Iterable, index):
        self.grouper = grouper
        self.data: Iterable = data
        self.index: int = index


class DetailData(DataBand):
    band_type = 'DetailData'


class GroupHeader(Band):
    reprint_on_new_page = False
    band_type = 'GroupHeader'
    expression: str = None
    band: DataBand = None
    field: str = None
    footer: 'GroupFooter' = None
    _datasource: DataSource = None
    _template_expression: Template = None

    @property
    def template_expression(self):
        if not self._template_expression:
            if not self.expression and self.field:
                self.expression = 'record.' + self.field
            assert self.expression
            if '"' in self.expression:
                self.expression = self.expression.replace('"', '')
            try:
                self._template_expression = report_env.from_string('{{ %s }}' % self.expression)
            except:
                print('Error preparing expression for', self.name)
                raise
        return self._template_expression

    def eval_condition(self, row, context: dict):
        context[self._datasource.name] = row
        return self.template_expression.render(**context)

    @property
    def datasource(self):
        if self._datasource is None:
            for child in self.children:
                if isinstance(child, (GroupHeader, DataBand)):
                    self._datasource = child.datasource
                    break
        return self._datasource

    def on_new_page(self, page: PreparedPage, context):
        super().prepare(page, context)

    def prepare(self, page: PreparedPage, context):
        self._context = context
        datasource = self.datasource
        datasource.open()
        data = datasource.data
        return self.process(data, page, context)

    def process(self, data: Iterable, page: PreparedPage, context):
        self.page.add_new_page_callback(self.on_new_page)
        groups = groupby(data, key=partial(self.eval_condition, context=context))
        databand = None
        datasource = self.datasource
        datasource_name = datasource and datasource.name
        for i, (grouper, lst) in enumerate(groups):
            lst = DataProxy(list(lst))
            group = Group(grouper, lst, i)
            context['group'] = group
            context[datasource_name] = lst
            page = super().prepare(page, context)

            for child in self.children:
                if datasource_name:
                    context[datasource.name] = lst
                if isinstance(child, DataBand):
                    page = child.process(lst, page, context)
                    databand = child
                elif isinstance(child, GroupHeader):
                    page = child.process(lst, page, context)
                else:
                    page = child.prepare(page, context)

        context[datasource_name] = DataProxy(datasource.data)

        self.page.remove_new_page_callback(self.on_new_page)
        if not self.parent and databand and databand.footer:
            page = databand.footer.prepare(page, context)

        return page


class GroupFooter(Band):
    band_type = 'GroupFooter'
    group_header: GroupHeader = None


class ReportTitle(Band):
    pass


class PageTitle(Band):
    pass


class ReportElement:
    report: Report = None
    element_type: str = None
    name: str = None
    left: float = 0
    top: float = 0
    height: float = None
    width: float = None

    def __init__(self, band: Band):
        self.band = band
        band.add_element(self)
        self.report = self.band.report
        self.report.objects.append(self)

    def process(self, context) -> dict:
        return {
            'type': self.element_type,
            'left': self.left,
            'top': self.top,
            'height': self.height,
            'width': self.width,
        }

    def prepare(self, stream: List, context):
        obj = self.process(context)
        if obj is not None:
            stream.append(obj)
        return obj


_re_number_fmt = re.compile(r'\.(\d)f')


class DisplayFormat:
    __slots__ = ('format', 'kind', 'decimal_pos')

    def __init__(self, format: str, kind: str):
        self.format: str = format
        self.kind: str = kind

    def update_format(self):
        if self.kind == 'Numeric':
            self.decimal_pos = _re_number_fmt.match(self.format)


class Font:
    name: str = None
    size: int = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: int = None


class Border:
    left: bool = False
    top: bool = False
    right: bool = False
    bottom: bool = False
    width = 1
    color: int = None
    style: int = None


class RecordHelper:
    def __init__(self, rec):
        self._rec = rec

    def __getattr__(self, item):
        return self._rec[item]

    def __getitem__(self, item):
        return self._rec[item]


class BrushStyle(Enum):
    NONE = 0
    SOLID = 1


class Highlight:
    fontName = ''
    fontSize: int = None
    color: int = None
    condition: str = None
    fillType = ''
    brushStyle = 0
    backColor: int = None
    _template: Template = None

    def eval_condition(self, context):
        if self._template is None:
            self._template = report_env.from_string('{{%s}}' % self.condition)
        return self._template.render(**context).strip() == 'True'


class Text(ReportElement):
    _field: str = None
    _template: Template = None
    bg_color: int = None
    brushStyle = 1
    auto_width = False
    can_grow = False
    can_shrink = False
    element_type = 'text'
    font: Font = None
    v_align: str = None
    h_align: str = None
    word_wrap = False
    allow_tags: bool = False
    allow_expressions: bool = True
    datasource: DataSource = None
    text: Optional[str] = None

    def __init__(self, band: Band, text: str = None):
        super().__init__(band)
        self.display_format: DisplayFormat = None
        self.font = Font()
        self.border = Border()
        self.text = text

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
            self._template = report_env.from_string(self.text, {'this': self})
        return self._template

    def template2(self, text: str):
        return report_env.from_string(text, {'this': self})

    def process(self, context) -> PreparedText:
        from .qt import TextRenderer
        new_obj = PreparedText()
        new_obj.height = self.height
        new_obj.width = self.width
        new_obj.left = self.left
        new_obj.top = self.top
        new_obj.allowTags = self.allow_tags
        if self.allow_expressions:
            try:
                new_obj.text = self.template.render(**self.band._context)
                if '${' in new_obj.text:
                    self.report._pending_objects.append((self.template2(new_obj.text.replace('${', '{{').replace('}', '}}')), new_obj))
            except Exception as e:
                print('Error evaluating expression', self.text)
                print(e)
                new_obj.text = '<Error>'
        else:
            new_obj.text = self.text
        new_obj.fontName = self.font.name or 'Arial'
        if self.font.size:
            new_obj.fontSize = self.font.size
        new_obj.fontBold = self.font.bold
        new_obj.fontItalic = self.font.italic
        new_obj.backColor = self.bg_color
        new_obj.brushStyle = self.brushStyle
        if self.highlight and self.highlight.eval_condition(context):
            new_obj.brushStyle = self.highlight.brushStyle
            new_obj.backColor = self.highlight.backColor
        new_obj.vAlign = self.v_align
        new_obj.hAlign = self.h_align
        new_obj.border = self.border
        new_obj.wordWrap = self.word_wrap
        if self.can_grow:
            new_obj.canGrow = True
            size = TextRenderer.calc_size(new_obj)
        return new_obj


class SysText(Text):
    pass


class Image(ReportElement):
    element_type = 'image'
    filename: str = None
    url: str = None
    picture: bytes = None
    _datasource: DataSource = None
    field: str = None

    def prepare(self, stream: List, context):
        img = PreparedImage()
        img.left = self.left
        img.top = self.top
        img.height = self.height
        img.width = self.width
        if self.field:
            img.picture = context[self.datasource.name][self.field]
        else:
            img.picture = self.picture
        stream.append(img)

    @property
    def datasource(self):
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        if isinstance(value, str):
            value = self.report.get_datasource(value)
        self._datasource = value


class Line(ReportElement):
    size = 0

    def __init__(self, band):
        super().__init__(band)
        self.border = Border()

    def prepare(self, stream: List, context):
        from .runtime import PreparedLine
        line = PreparedLine()
        line.left = self.left
        line.top = self.top
        line.width = self.width
        line.height = self.height
        line.size = self.size
        stream.append(line)


class SubReport(ReportElement):
    page_name: str = None
    _report_page: Page = None
    _overlapped = False
    _x = _y = 0

    @property
    def bands(self):
        return self.report_page.bands

    @property
    def report_page(self) -> Page:
        if self.page_name:
            return self.report[self.page_name]

    @report_page.setter
    def report_page(self, value: Page):
        self.page_name = value.name
        value.subreport = self

    def prepare(self, page: PreparedPage, context):
        # print target page
        cur_page = page
        try:
            page.x = self.left + self._x
            page.y = self.top + self._y
            for band in self.bands:
                if isinstance(band, GroupHeader):
                    page = band.prepare(page, context) or page
                elif isinstance(band, DataBand) and band.group_header is None:
                    page = band.prepare(page, context) or page
        finally:
            cur_page.x = self._x
            cur_page.y = self._y


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


class Table(ReportElement):
    def __init__(self, band):
        super().__init__(band)
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

