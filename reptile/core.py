from typing import List, Optional
import locale
from enum import Enum
from decimal import Decimal
import datetime
import jinja2
from jinja2 import contextfunction
from lxml import etree
from PySide2.QtGui import QPageSize, QPainter, QTextDocument, QPen, QFont, QColor, QFontMetrics
from PySide2.QtGui import QPixmap
from PySide2.QtCore import QRectF, Qt, QLine, QSize, QRect
from .utils import total, avg
from .style import Style, Border, Fill


@contextfunction
def finalize(ctx, value):
    if value is None:
        return ''
    this = ctx.parent.get('this')
    if isinstance(value, (float, Decimal)):
        return locale.format_string(FormatSettings.numeric_format, value, grouping=True)
    if isinstance(value, datetime.date) and FormatSettings.date_format:
        return value.strftime(FormatSettings.date_format)
    if isinstance(value, datetime.datetime) and FormatSettings.datetime_format:
        return value.strftime(FormatSettings.datetime_format)
    return value


class FormatSettings:
    numeric_format: str = '%.2f'
    date_format: str = None
    datetime_format: str = None


TAG_REGISTRY = {}


class ReportElement:
    def __init__(self, parent=None, report=None):
        self.name: Optional[str] = None
        self.objects = []
        self.content: Optional[str] = None
        self.report: Report = report
        self.parent = parent
        if not report and isinstance(parent, Report):
            self.report = report

    def add_object(self, child):
        self.objects.append(child)
        child.parent = self
        child.report = self.report

    def read_xml(self, node):
        for k, v in node.attrib.items():
            setattr(self, k.replace('-', '_'), v)
        text = node.text and node.text.strip()
        if text:
            self.content = text
        for child in node:
            obj = self.create_element(child)
            if obj is None:
                continue
            if isinstance(self, Report):
                obj.report = self
            else:
                obj.report = self.report
            if obj not in self.objects:
                self.objects.append(obj)
            obj.read_xml(child)

    def create_element(self, child):
        if child.tag in REGISTRY:
            return REGISTRY[child.tag.lower()](self)

    def init(self, page):
        pass


class ReportEngine:
    env = None

    @classmethod
    def create_template_env(cls):
        if cls.env:
            return cls.env
        env = jinja2.Environment(finalize=finalize)
        env.globals['sum'] = sum
        env.globals['total'] = total
        env.globals['avg'] = avg
        env.globals['count'] = len
        if cls.env is None:
            cls.env = env
        return env


class Report(ReportElement):
    env = None

    def __init__(self, filename=None, title=None, default_connection=None, env=None, params=None):
        super().__init__()
        self.pages: List[Page] = []
        self.totals = []
        self.datasources = {}
        self.filename: str = filename
        self.document: Optional[Document] = None
        if env is None and not self.env:
            self.env = ReportEngine.create_template_env()
        else:
            self.env = env
        self._preparing = False
        self.title: str = title
        self.styles = {}
        self.default_connection: Connection = default_connection
        self.default_datasource: Optional[DataSource] = None
        if params:
            self.prepared_params = params
        else:
            self.prepared_params = None

    def from_string(self, s: str):
        self.read_xml(etree.fromstring(s))

    def load_file(self, filename: str):
        if filename.endswith('.xml'):
            with open(filename, 'rb') as f:
                self.from_string(f.read())

    def add_page(self) -> 'Page':
        page = Page(self)
        page.report = self
        self.pages.append(page)
        return page

    @property
    def preparing(self):
        return self._preparing

    def prepare(self):
        self._preparing = True
        if self.pages:
            page = self.pages[0]
        else:
            # add a page
            page = self.add_page()

        # initialize the loaded objects
        for child in self.objects:
            if isinstance(child, Band):
                page.add_band(child)
            elif not isinstance(child, Widget):
                child.init(page)

        try:
            self.document = Document(self)
            for page in self.pages:
                page.init()
                page.prepare(self.document)
            return self.document
        finally:
            self._preparing = False

    def register_datasource(self, datasource):
        self.datasources[datasource.name] = datasource


mm = 3.77953
cm = 37.7953


class Document:
    """
    Prepared report document.
    """
    def __init__(self, report):
        self.report: Report = report
        self.pages: List[PreparedPage] = []

    def add_page(self):
        page = PreparedPage()
        self.pages.append(page)
        return page


class PreparedPage:
    height = 0
    width = 0

    def __init__(self):
        self.bands: List[PreparedBand] = []

    def add_band(self):
        band = PreparedBand()
        self.bands.append(band)
        return band


class PreparedBand:
    report = None
    left = 0
    top = 0
    height = 0
    width = 0
    context = {}
    fill = None

    def __init__(self):
        self.objects: List[Widget] = []

    @property
    def bottom(self):
        return self.top + self.height

    def draw(self, painter: QPainter):
        if self.fill:
            r = QRectF(self.left, self.top, self.width, self.height)
            painter.fillRect(r, self.fill.color_1)


class ReportObject(ReportElement):
    def __init__(self, parent=None):
        super().__init__(parent)


class Widget(ReportObject):
    height = 19
    width = 100

    def __init__(self, band=None):
        super().__init__(band)
        self.left = 0
        self.top = 0
        self.page: Optional[Page] = None
        self.parent: 'Band' = band
        self._prepared = False
        if band:
            band.objects.append(self)
            self.report = band.report
        self.cols = None

    def init(self, page):
        self.report = page.report
        self.page = page

    def set_size(self, size: QSize):
        self.height = size.height()
        self.width = size.width()

    def calc_size(self):
        return QSize(self.height, self.width)

    def render(self, prepared_band):
        obj = self.__class__(prepared_band)
        return obj

    def prepare(self, prepared_band):
        obj = self.render(prepared_band)
        obj.set_size(obj.calc_size())
        return obj

    @property
    def y(self):
        return self.top + self.parent.top

    @property
    def x(self):
        return self.left + self.parent.ox

    @property
    def bottom(self):
        return self.top + self.height


class Margin:
    left = 5 * mm
    top = 5 * mm
    right = 5 * mm
    bottom = 5 * mm


class Page(ReportObject):
    _x = _y = _ay = _ax = 0
    _page_header = None
    _page_footer = None
    _report_title = None
    bottom = 0
    title_before_header = True
    reset_page_number = False

    def __init__(self, report=None):
        super().__init__(report)
        self._page_size = None
        self.width = None
        self.height = None
        self.page_size = QPageSize.A4
        self.bands = []
        self.document = None
        self.margin = Margin()
        self.is_first_page = True
        self._current_page = None
        self.summary: Optional[ReportSummary] = None
        self.context = None

    def add_band(self, band):
        self.bands.append(band)
        band.page = self

    def init(self):
        self.is_first_page = True
        for band in self.bands:
            band.init(self)

    def prepare(self, document):
        self.context = ctx = {}
        self.document = document
        for band in self.bands:
            if isinstance(band, ReportTitle):
                self._report_title = band
            elif isinstance(band, PageFooter):
                self._page_footer = band
            elif isinstance(band, ReportSummary):
                self.summary = band
        special_bands = (self._report_title, self._page_footer, self.summary)

        self.new_page()
        for band in self.bands:
            if band not in special_bands:
                if isinstance(band.parent, Band):
                    continue
                band.prepare(self, ctx)
        if self.summary:
            self.summary.prepare(self, ctx)
        self._end()

    @property
    def page_size(self):
        return self._page_size

    @page_size.setter
    def page_size(self, page_size):
        self._page_size = QPageSize(page_size)
        _size = self._page_size.size(QPageSize.Millimeter)
        self.width = _size.width() * mm
        self.height = _size.height() * mm

    @property
    def client_width(self):
        return self.width - self.margin.left - self.margin.right

    def _begin(self):
        if self.is_first_page and self._report_title:
            self._report_title.prepare(self, self.context)
        if self._page_footer:
            self._ay -= self._page_footer.height
        self.is_first_page = False

    def _end(self):
        # draw page footer
        if self._page_footer:
            self._ay += self._page_footer.height
            self._y = self.height - self.margin.bottom - self._page_footer.height
            self._page_footer.prepare(self, self.context)

    def new_page(self):
        if self._current_page and self._page_footer:
            # print footer band
            self._end()
        self._x = self.margin.left
        self._y = self.margin.top
        self._ay = self.height - self.margin.top - self.margin.bottom
        self._current_page = self.document.add_page()
        self._current_page.width = self.width
        self._current_page.height = self.height
        self._begin()


class Band(Widget):
    auto_height = False
    _page: 'Page' = None

    def __init__(self, page=None):
        super().__init__()
        self.text: Optional[str] = None
        self.fill = Fill()
        self.height = 20
        self.page = page
        if isinstance(page, Page):
            page.add_band(self)
        self.children: List[Band] = []
        self.totals = []
        self.reset_totals = []
        self.border = Border()
        self.ox = 0
        self.ax = 0
        self.cols = None
        self.col_width = 0

    def read_xml(self, xml):
        super().read_xml(xml)
        if self.content:
            self.text = self.content

    def init(self, page):
        super().init(page)
        self.width = page.client_width
        for obj in self.objects:
            obj.init(page)
        for child in self.children:
            child.init(page)
        if self.content:
            text = Text()
            text.text = self.content
            text.width = self.width
            self.add_object(text)

    def render(self, prepared_band):
        band = super().render(prepared_band)
        band.auto_height = self.auto_height
        band.height = self.height
        band.fill = self.fill
        return band

    def add_band(self, band):
        band._page = self._page
        band.parent = self
        self.children.append(band)

    def add_object(self, obj):
        self.objects.append(obj)
        obj.parent = self
        obj.report = self.report

    def prepare(self, page, context):
        ctx = context
        if self.name:
            ctx[self.name] = self
        if context:
            ctx.update(context)
        for total in self.totals:
            ctx[total.name] = total.compute(context)
        for total in self.report.totals:
            ctx[total.name] = total.value
        band = PreparedBand()
        band.left = self.ox
        band.context = ctx
        band.height = self.height
        band.width = self.page.client_width
        self.ox = page._x
        y = 0
        objs = []
        for obj in self.objects:
            obj = obj.prepare(band)
            objs.append(obj)
            if obj.bottom > y:
                y = obj.bottom
        if self.auto_height and band.height != y:
            band.height = y
            for obj in objs:
                if obj.can_grow and obj.bottom < band.height:
                    obj.height = band.height - obj.top
        if isinstance(band, DataBand):
            band.height -= 1
        self.add_prepared_band(page, band)
        for total in self.reset_totals:
            total.value = 0
        return band

    def add_prepared_band(self, page, band):
        """
        Calculate if there's enough space available to print the band, else, print it in a new page.
        :param band:
        :return:
        """
        if page._ay < band.height:
            page.new_page()
            self.on_new_page(page, band.context)
        page._ay -= band.height
        band.top = page._y
        page._y = band.bottom
        page._current_page.bands.append(band)

    def on_new_page(self, page, context):
        pass


class HeaderBand(Band):
    pass


class FooterBand(Band):
    pass


class ReportTitle(Band):
    pass


class ReportSummary(Band):
    pass


class DataProxy:
    def __init__(self, iterable):
        self.iterable = iterable

    def __getitem__(self, item):
        return [obj[item] for obj in self.iterable]

    def __iter__(self):
        return self.iterable or []

    def __len__(self):
        return len(self.iterable)


class DataBand(Band):
    _datasource = None
    datasource_name: str = None
    header: HeaderBand = None
    footer: FooterBand = None
    group_header = None
    row_index = -1
    rows = None
    max_rows = None
    even_style = None
    even: bool = None
    counter = 0

    def prepare(self, page, ctx):
        self.counter = self.row_index
        if not self.datasource:
            records = range(self.rows)
        else:
            records = self.datasource
        ctx['records'] = DataProxy(records)
        for row in records:
            self.row_index += 1
            if self.datasource:
                ctx.update(self.datasource.context)
            else:
                ctx['row'] = self.row_index
                self.even = ctx['even'] = bool(self.row_index % 2)
                ctx['odd'] = not self.even
            ctx['record'] = row
            if self.datasource_name:
                ctx[self.datasource_name] = row
            # prepared = super().prepare(page, context=ctx)
            self.prepare_row(page, ctx)

    def add_band(self, band):
        super().add_band(band)
        if isinstance(band, HeaderBand):
            self.header = band
        elif isinstance(band, FooterBand):
            self.footer = band

    @property
    def datasource(self):
        if self._datasource is None and self.datasource_name:
            self._datasource = self.report.datasources[self.datasource_name]
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        if value is not None and not isinstance(value, DataSource):
            self._datasource = DataSource(value)
        else:
            self._datasource = value

    def on_new_page(self, page, context):
        if self.header:
            self.header.prepare(page, context)

    def begin(self, page, context):
        if self.header:
            self.header.prepare(page, context)

    def end(self, page, context):
        if self.footer:
            self.footer.prepare(page, context)

    def prepare_row(self, page, context):
        self.counter = context['row']
        prepared = super().prepare(page, context)
        if self.even_style and self.even:
            prepared.fill = self.report.styles[self.even_style].fill


class MasterData(DataBand):
    pass


class PageFooter(FooterBand):
    pass


class Connection(ReportObject):
    connection_string: str = None

    def execute(self, sql):
        raise NotImplemented()


class Params(ReportElement):
    pass


class Param(ReportElement):
    pass


class Data(ReportElement):
    def create_element(self, child):
        return REGISTRY[child.tag]()


class DataSource(ReportObject):
    line = 0
    count = 0

    def __init__(self, data=None, connection: Connection=None):
        super().__init__()
        self.name: Optional[str] = None
        self.alias: Optional[str] = None
        self._data = data
        self._connection = connection

    def read_xml(self, node):
        super().read_xml(node)
        if not self.name:
            self.report.default_datasource = self

    @property
    def connection(self):
        if self._connection is None:
            self._connection = self.report.default_connection
        return self._connection

    @property
    def data(self):
        return self._data

    def __iter__(self):
        for i, item in enumerate(self.data):
            if i == 0:
                self.count = len(self.data)
            self.line = i
            yield item

    def __getitem__(self, item):
        return self.data[item]

    def __len__(self):
        return len(self.data)

    @property
    def context(self):
        even = self.line % 2
        odd = not even
        return {
            'row_index': self.line,
            'line': self.line,
            'count': self.count,
            'even': even,
            'odd': odd,
        }


class Query(DataSource):
    sql: str = None

    def __init__(self):
        super().__init__()
        self.params = {}

    @property
    def data(self):
        if self._data is None:
            if self.report.prepared_params:
                args = [self.report.prepared_params]
            else:
                args = [{}]
            self._data = list(self.connection.execute(self.sql, *args))
        return self._data

    def close(self):
        self._data = None

    def read_xml(self, node):
        super().read_xml(node)
        self.sql = node.text


class UNDEFINED:
    pass


class DataGroup:
    value = UNDEFINED
    parent = None

    def __init__(self):
        self._records = []

    @property
    def records(self):
        return DataProxy(self._records)


class GroupHeader(HeaderBand):
    child = None
    _data_band: DataBand = None
    footer: FooterBand = None
    expression = None
    _template_expression = None
    _last_val = UNDEFINED
    group = None
    field: str = None

    @property
    def template_expression(self):
        if not self._template_expression:
            if not self.expression and self.field:
                self.expression = 'record.' + self.field
            assert self.expression
            if '"' in self.expression:
                self.expression = self.expression.replace('"', '')
            self._template_expression = self.report.env.from_string('{{ %s }}' % self.expression)
        return self._template_expression

    def _end(self, page, context):
        self._last_val = UNDEFINED
        if self.child:
            self.child._end(page, context)
        if self.footer:
            if self.datasource.name:
                self.context[self.datasource.name] = self.context['records']
                if self.datasource.alias:
                    self.context[self.datasource.alias] = self.context['records']
            self.footer.prepare(page, context)

    def prepare_record(self, record, page, context, finish=False):
        context['group'] = self.group
        if not finish:
            new_val = self.template_expression.render(context)
        else:
            new_val = UNDEFINED
        if self._last_val != new_val:
            if self._last_val is not UNDEFINED:
                # print the group header
                super().prepare(page, context=context)
                # save the current record and print the data band
                old_rec = context['record']
                self.band.begin(page, context)
                for i, rec in enumerate(self.group._records):
                    self.band.even = i % 2
                    context['line'] += 1
                    context['row'] = i
                    context['record'] = rec
                    context['even'] = self.band.even
                    context['odd'] = not self.band.even
                    if self.datasource and self.datasource.name:
                        context[self.datasource.name] = rec
                        context[self.datasource.alias] = rec
                    self.band.prepare_row(page, context)
                self.band.end(page, context)
                self._end(page, self.context)
                self.group._records = []
                context['record'] = old_rec
            self.group.value = new_val
            self._last_val = new_val
        self.group._records.append(record)
        # if self.child:
        #     self.child.prepare_record(record, page, new_context)
        # else:
        #     self.data_band.prepare_row(page, new_context)
        # if has_new_val:
        #     self.grouper.records = []

    def prepare(self, page, context):
        self.context = context
        if self.datasource is not None:
            ds = list(self.datasource.data)
            dp = DataProxy(ds)
            self.context['records'] = dp
            self.context['line'] = -1
            for obj in ds:
                self.context['record'] = obj
                if self.datasource.name:
                    self.context[self.datasource.name] = obj
                    if self.datasource.alias:
                        self.context[self.datasource.alias] = obj
                self.prepare_record(obj, page, self.context)
            if ds:
                self.prepare_record(obj, page, self.context, True)

    def init(self, page):
        super().init(page)
        self.group = DataGroup()
        if isinstance(self.parent, GroupHeader):
            self.group.parent = self.parent.group
        for child in self.objects:
            if isinstance(child, GroupHeader):
                self.child = child
            elif isinstance(child, DataBand):
                self._data_band = child
            elif isinstance(child, GroupFooter):
                self.footer = child
            child.init(page)
        if self.text:
            self.objects[-1].font.setBold(True)

    def add_band(self, band):
        super().add_band(band)
        if isinstance(band, DataBand):
            self.band = band

    @property
    def datasource(self):
        if self.band:
            return self.band.datasource


class GroupFooter(FooterBand):
    pass


class StretchMode(Enum):
    sum = 0
    count = 1


class Total:
    name = None
    expression = None
    total_type = 'sum'
    _band = None
    _print_on_band = None
    value = 0

    def __init__(self, report):
        self.report = report
        self.report.totals.append(self)

    def compute(self, context):
        if self.total_type == 'sum':
            assert self.expression
            val = eval(self.expression, {}, context)
            self.value += val
        else:
            self.value += 1
        return self.value

    @property
    def band(self):
        return self._band

    @band.setter
    def band(self, value):
        self._band = value
        self._band.totals.append(self)

    @property
    def print_on_band(self):
        return self._print_on_band

    @print_on_band.setter
    def print_on_band(self, value):
        self._print_on_band = value
        self._print_on_band.reset_totals.append(self)


class Text(Widget):
    can_grow = False
    can_shrink = False
    auto_width = False
    text = None
    allow_tags = False
    allow_expressions = True
    _h_align = 0
    _v_align = Qt.AlignVCenter
    datasource_name: str = None
    _doc = QTextDocument()
    _label = None
    _template = None
    _rendered_text = None
    _word_wrap = False
    _text_word_wrap = 0
    paddingX = 2
    paddingY = 2
    format_type: str = None
    display_format: str = None

    def __init__(self, band=None):
        super().__init__(band)
        self.border = Border()
        self.font = QFont()
        self.font.setPointSize(8)

    def read_xml(self, node):
        super().read_xml(node)
        if self.content:
            self.text = self.content

    @property
    def bold(self):
        return self.font.bold()

    @bold.setter
    def bold(self, value):
        self.font.setBold(bool(value))

    @property
    def italic(self):
        return self.font.italic()

    @italic.setter
    def italic(self, value):
        self.font.setItalic(bool(value))

    @property
    def underline(self):
        return self.font.underline()

    @underline.setter
    def underline(self, value):
        self.font.setUnderline(bool(value))

    @property
    def h_align(self):
        return self._h_align

    @h_align.setter
    def h_align(self, value):
        if isinstance(value, str):
            if value == 'right':
                value = Qt.AlignRight
            elif value == 'center':
                value = Qt.AlignHCenter
        self._h_align = value

    @property
    def v_align(self):
        return self._v_align

    @v_align.setter
    def v_align(self, value):
        if isinstance(value, str):
            if value == 'top':
                value = Qt.AlignTop
            elif value == 'center':
                value = Qt.AlignVCenter
            elif value == 'bottom':
                value = Qt.AlignBottom
        self._v_align = value

    @property
    def word_wrap(self) -> bool:
        return self._word_wrap

    @word_wrap.setter
    def word_wrap(self, value: bool):
        self._word_wrap = value
        if value:
            self._text_word_wrap = Qt.TextWordWrap

    @property
    def template(self):
        if self._template is None and self.text:
            self._template = self.report.env.from_string(self.text)
        return self._template

    def _text_flags(self):
        return self.h_align | self.v_align | self._text_word_wrap

    def render(self, prepared_band):
        obj = super().render(prepared_band)
        obj.left = self.x
        obj.top = self.top
        obj.width = self.width
        obj.height = self.height
        obj.allow_tags = self.allow_tags
        obj.h_align = self.h_align
        obj.v_align = self.v_align
        obj.border = self.border
        obj.font = self.font
        obj.can_grow = self.can_grow
        obj.can_shrink = self.can_shrink
        obj._text_word_wrap = self._text_word_wrap
        if self.allow_expressions and self.template:
            prepared_band.context['this'] = self
            obj.text = self.template.render(prepared_band.context)
        else:
            obj.text = self.text
        return obj

    def calc_size(self):
        if self.can_grow or self.can_shrink or self.auto_width:
            rect = QRect(0, self.top, self.width - self.paddingX * 2 - self.border.width * 2, self.height)
            fm = QFontMetrics(self.font)
            flags = self._text_flags()
            r = fm.boundingRect(0, 0, rect.width(), 0, flags, self.text)
            if (self.can_shrink and self.height > r.height()) or (self.can_grow and self.height < r.height()):
                rect.setHeight(r.height())
            if self.auto_width:
                rect.setWidth(r.width() + self.border.width * 2)
            return QSize(rect.width() + self.paddingX * 2 + self.border.width * 2, rect.height() + self.border.width * 2)
        return QSize(self.width, self.height)

    def draw(self, painter: QPainter):
        w = self.width - self.paddingX * 2
        h = self.height
        x = self.left + self.paddingX
        y = self.y
        if self.border:
            w -= self.border.width
            h -= self.border.width * 2
            x += self.border.width
            y += self.border.width
        if self.allow_tags:
            doc = self._doc
            doc.setTextWidth(self.width)
            opt = doc.defaultTextOption()
            if self.h_align:
                opt.setAlignment(self.h_align)
            doc.setDefaultTextOption(opt)
            doc.setHtml(self.text)
            doc.setDocumentMargin(0)
            painter.save()
            painter.translate(0, self.y)
            y = self.top + self.border.width * 2
            doc.setDefaultFont(self.font)
            doc.drawContents(painter, QRectF(x, y, w, h))
            painter.restore()
        else:
            painter.save()
            painter.setFont(self.font)
            flags = self._text_flags()
            painter.drawText(QRectF(x, y, w, h), flags, self.text)
            painter.restore()
        if self.border:
            old_pen = painter.pen()
            pen = QPen(self.border.color, self.border.width)
            painter.setPen(pen)
            painter.drawLines(self.border.get_lines(self.left, self.y, self.left + self.width, self.y + self.height))
            painter.setPen(old_pen)


class Image(Widget):
    _img = None
    auto_size = False
    data_source = None
    field = None
    filename = None
    height = 40
    width = 40
    stretch = False

    def render(self, prepared_band):
        obj = super().render(prepared_band)
        obj.filename = self.filename
        obj.stretch = self.stretch
        obj.auto_size = self.auto_size
        if self._img is None:
            self._img = QPixmap(self.filename)
        obj._img = self._img

        w = obj.width
        h = obj.height
        if obj.auto_size:
            w = obj._img.width()
            h = obj._img.height()
        elif not obj.stretch and obj._img.width() > w or obj._img.height() > h:
            img = obj._img.scaled(obj.width, obj.height, Qt.KeepAspectRatio)
            w = img.width()
            h = img.height()
        obj.width = w
        obj.height = h
        return obj

    def draw(self, painter: QPainter):
        painter.drawPixmap(self.left, self.y, self.width, self.height, self._img)


class Div(Text):
    def __init__(self, *args):
        super().__init__(*args)
        self.cols = 1

    def init(self, page):
        if not self.parent.cols:
            self.parent.cols = [int(obj.cols) for obj in self.parent.objects]
            self.parent.col_width = self.parent.width / sum(self.parent.cols)
        self.width = self.cols * self.parent.col_width
        self.left = self.parent.ax
        self.parent.ax += self.width


class CalcText(Text):
    pass


REGISTRY = {
    'reporttitle': ReportTitle,
    'groupheader': GroupHeader,
    'groupfooter': GroupFooter,
    'data': Data,
    'query': Query,
    'params': Params,
    'param': Param,
    'text': Text,
    'div': Div,
    'calctext': CalcText,
    'summary': ReportSummary,
}
