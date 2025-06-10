from typing import List, Optional, Iterable, TypedDict
from functools import partial
from itertools import groupby
from collections import defaultdict
from decimal import Decimal

from jinja2 import Template

from reptile import EnvironmentSettings
from reptile.runtime import PreparedPage, PreparedBand
from reptile.core import ReportObject, BasePage, Report, Margin, mm, VAlign, Font
from reptile.data import DataSource


class Page(BasePage):
    _page_header = None
    _page_footer = None
    _report_title = None
    _first_time = False
    _bottom_height = 0
    report: Report = None
    _context: dict = None
    _current_page: PreparedPage = None
    width: float = 0
    height: float = 0
    title_before_header = False
    reset_page_number = False
    stream = None
    subreport = None
    _pending_operations = None
    watermark: 'Watermark' = None

    def __init__(self):
        self.height = 297 * mm
        self.width = 210 * mm
        self.callbacks = []
        self.bands: List['Band'] = []
        self.margins = Margin()
        self._page_size = None
        self.orientation = 'portrait'
        self.watermark = Watermark()

    def find_object(self, name: str):
        for band in self.bands:
            if band.name == name:
                return band
            for obj in band.objects:
                if obj.name == name:
                    return obj
        return None

    @property
    def margin(self):
        return self.margins

    @margin.setter
    def margin(self, value):
        self.margins = value

    def load(self, structure: dict):
        self.height = structure.get('height', self.height)
        self.width = structure.get('width', self.width)
        self._pending_operations = defaultdict(list)
        self.orientation = structure.get('orientation', self.orientation)
        self.title_before_header = structure.get('titleBeforeHeader', self.title_before_header)
        bands = {}
        if 'watermark' in structure:
            self.watermark = Watermark()
            self.watermark.load(structure['watermark'])
        for b in structure['bands']:
            band = TAG_REGISTRY[b['type']]()
            self.add_band(band)
            band.load(b)
            bands[band.name] = band
        for pend, funcs in self._pending_operations.items():
            for fn in funcs:
                fn(bands[pend])

    def find_band(self, name: str):
        for band in self.bands:
            if band.name == name:
                return band

    def dump(self) -> dict:
        return {
            'type': 'banded',
            'height': self.height,
            'width': self.width,
            'name': self.name,
            'margins': self.margins.dump(),
            'bands': [band.dump() for band in self.bands],
            'pageSize': self._page_size,
            'orientation': self.orientation,
        }

    def add_band(self, band: 'Band'):
        if band.page != self:
            self.bands.append(band)
            band.page = self

    def prepare(self, stream: List):
        self._context = self.report._context
        self.stream = stream
        # detect special bands
        for band in self.bands:
            if isinstance(band, ReportTitle):
                self._report_title = band
            elif isinstance(band, PageHeader):
                self._page_header = band
            elif isinstance(band, PageFooter):
                self._page_footer = band

        # adjust band structure
        for band in self.bands:
            if isinstance(band, GroupHeader) and band.footer:
                band.footer.group_header = band
                if band.parent:
                    band.parent.children.append(band)
            elif isinstance(band, DataBand) and band.group_header:
                band.group_header.children.append(band)
            elif isinstance(band, GroupFooter):
                band.group_header.children.append(band)

        self._first_time = True
        page = self.new_page(self._context)

        for band in self.bands:
            # Only root bands should be processed here
            if isinstance(band, DataBand) and band.group_header:
                continue
            if band.parent is None and isinstance(band, (GroupHeader, DataBand)):
                page = band.prepare(page, self._context) or page
            elif band.__class__ is Band:
                # direct print
                page = band.prepare(page, self._context)

        self.end_page(page, self._context)

    def new_page(self, context):
        is_first_time = self._first_time
        self._first_time = False
        if self._current_page is not None:
            self.end_page(self._current_page, context)
        page = PreparedPage(self.height, self.width, self.margin)
        page.watermark = self.watermark
        self.report.page_count += 1
        page.index = self.report.page_count
        context['page_index'] = page.index
        page.bands = []

        if is_first_time and self.title_before_header and self._report_title:
            self._report_title.prepare(page, context)
        if self._page_header:
            self._page_header.prepare(page, context)
        if is_first_time and not self.title_before_header and self._report_title:
            self._report_title.prepare(page, context)

        if self._page_footer:
            page.ay -= self._page_footer.height
        self._current_page = page
        self.report.stream.pages.append(page)
        for cb in self.callbacks:
            cb(page, context)
        return page

    def end_page(self, page: PreparedPage, context):
        if self._page_footer:
            page.ay += self._page_footer.height + self._bottom_height
            page.y = page.ay - self._page_footer.height
            self._page_footer.prepare(page, context)
        self._bottom_height = 0

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


class Band(ReportObject):
    background: int = None
    height: int = 40
    width: int = None
    left: int = None
    top: int = None
    _page: Page = None
    _parent: 'Band' = None
    _context: dict = None
    band_type = 'Band'
    auto_height = False
    child_band: 'ChildBand' = None
    print_on_bottom = False
    _x = _y = 0

    def __init__(self, page: Page=None):
        if page:
            self.page = page
            self.report = page.report
        self.objects: List['ReportObject'] = []
        self.children: List['Band'] = []
        self.subreports: List['SubReport'] = []

    def load(self, data: dict):
        self.height = data.get('height', self.height)
        self.width = data.get('width', self.width or (self._page and self._page.width))
        self.name = data.get('name')
        self.print_on_bottom = data.get('printOnBottom', self.print_on_bottom)
        if child_band := data.get('childBand'):
            self.page._pending_operations[child_band].append(partial(setattr, self, 'child_band'))

        for obj in data['objects']:
            widget = TAG_REGISTRY[obj['type']]()
            self.add_object(widget)
            widget.load(obj)

    def dump(self) -> dict:
        return {
            'type': self.band_type,
            'height': self.height,
            'width': self.width,
            'name': self.name,
            'objects': [obj.dump() for obj in self.objects],
        }

    def add_band(self, band: 'Band'):
        band.parent = self

    def add_object(self, obj: 'ReportElement'):
        # if isinstance(element, SubReport):
        #     self.subreports.append(element)
        # else:
        #     self.objects.append(element)
        self.objects.append(obj)
        if obj.parent != self:
            obj.parent = self

    def prepare(self, page: PreparedPage, context):
        page = self.prepare_objects(page, context)
        # if self.subreports:
        #     self.prepare_subreports(page, context)
        if self.child_band:
            page = self.child_band.prepare(page, context)
        return page

    def prepare_objects(self, page: PreparedPage, context):
        # from .subreport import SubReport
        context = self._context = context or self.page._context
        band = PreparedBand()
        band.band_type = self.band_type
        objs = band.objects = []
        band.height = self.height
        band.width = self.width
        if self.print_on_bottom:
            band.left = page.x
            band.top = page.ay - band.height
        else:
            band.left = page.x
            band.top = page.y
        for obj in self.objects:
            # if isinstance(obj, SubReport):
            #     obj.prepare(page, context)
            # else:
            new_obj = obj.prepare(objs, context)
            if new_obj and (new_obj.height + new_obj.top) > band.height:
                band.height = new_obj.height + new_obj.top
        band.bottom = band.top + band.height
        if self.page.report._level > 1 and int(band.bottom) > int(page.ay):
            page = self.page.new_page(context)
            band.set_page(page)
        if not (
            (band.band_type == "GroupHeader")
            and band.objects
            and (band.bottom + band.objects[0].height + band.objects[0].top) > page.ay
        ):
            page.bands.append(band)
        if self.print_on_bottom:
            page.ay -= band.height
            self.page._bottom_height += band.height
        else:
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
        if self._page is not None and self in self._page.bands:
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


class FooterBand(Band):
    band_type = 'FooterBand'


class HeaderBand(Band):
    band_type = 'HeaderBand'


class ReportSummary(Band):
    band_type = 'ReportSummary'


class ChildBand(Band):
    band_type = 'ChildBand'


class ReportTitle(Band):
    pass


class PageTitle(Band):
    pass


class RecordHelper:
    def __init__(self, rec):
        self._rec = rec

    def __getattr__(self, item):
        if isinstance(self._rec, dict):
            return self._rec[item]
        return getattr(self._rec, item)

    def __getitem__(self, item):
        return self._rec[item]


class Group:
    def __init__(self, grouper, data: List, index):
        self.grouper = grouper
        self.data: List = data
        self.index: int = index

    @property
    def count(self):
        return len(self.data)


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

    def __getitem__(self, item):
        return self.data[0][item]

    def __getitem__(self, item):
        return self.data[0][item]

    def __len__(self):
        return len(self.data)


class DataBand(Band):
    band_type = 'DataBand'
    _datasource: DataSource = None
    row_count: int = None
    header: 'HeaderBand' = None
    footer: 'FooterBand' = None
    group_header: 'GroupHeader' = None
    expression: str = None

    def load(self, structure: dict):
        super().load(structure)
        self.datasource = structure.get('datasource')
        self.expression = structure.get('expression')
        if name := structure.get('groupHeader'):
            self.page._pending_operations[name].append(partial(setattr, self, 'group_header'))
        if name := structure.get('header'):
            self.page._pending_operations[name].append(partial(setattr, self, 'header'))
        if name := structure.get('footer'):
            self.page._pending_operations[name].append(partial(setattr, self, 'footer'))

    def dump(self) -> dict:
        return {
            **super().dump(),
            'datasource': self.datasource,
            # 'row_count': self.row_count,
            'header': self.header.name if self.header else None,
            'footer': self.footer.name if self.footer else None,
            'expression': self.expression,
            # 'group_header': self.group_header.dump() if self.group_header else None,
        }

    def prepare(self, page: PreparedPage, context):
        data = self.data
        self._context = context
        if data:
            return self.process(data, page, context)

    def process(self, data: Iterable, page: PreparedPage, context: dict):
        context.setdefault('line', 0)

        # print the header band
        if self.header and not self.group_header:
            page = self.header.prepare(page, context)

        self._context = context
        for i, row in enumerate(data):
            row = RecordHelper(row) if isinstance(row, dict) else row
            if self.datasource and self.datasource.name:
                context[self.datasource.name] = row
            context['record'] = row
            context['row'] = i + 1
            context['line'] += 1
            if self.name:
                context[self.name] = row
            even = context['even'] = bool(i % 2)
            context['odd'] = not even
            page = super().prepare(page, context)
        if self.datasource:
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
        elif self.expression:
            return self.page.report._context[self.expression]
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

class GroupHeader(Band):
    reprint_on_new_page = False
    band_type = 'GroupHeader'
    expression: str = None
    _band: DataBand = None
    field: str = None
    footer: 'GroupFooter' = None
    _datasource: DataSource = None
    _template_expression: Template = None

    def load(self, structure: dict):
        super().load(structure)
        self.expression = structure.get('expression')
        if name := structure.get('dataBand'):
            self.page._pending_operations[name].append(partial(setattr, self, 'band'))
        if name := structure.get('footer'):
            self.page._pending_operations[name].append(partial(setattr, self, 'footer'))

    @property
    def band(self):
        return self._band

    @band.setter
    def band(self, value):
        self._band = value
        if value:
            self._datasource = value.datasource

    @property
    def template_expression(self):
        if not self._template_expression:
            if not self.expression and self.field:
                self.expression = 'record.' + self.field
            assert self.expression, 'Group expression must be specified'
            if '"' in self.expression:
                self.expression = self.expression.replace('"', '')
            try:
                self._template_expression = EnvironmentSettings.env.from_string('{{ %s }}' % self.expression)
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
            if self.band and self.band.datasource:
                self._datasource = self.band._datasource
            else:
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


class Watermark:
    enabled = False
    text = None
    valign: VAlign = VAlign.CENTER
    font: Font = None
    image = None
    angle = 0
    opacity = 0.7

    def __init__(self):
        pass

    def load(self, structure: dict):
        self.enabled = structure.get('enabled', self.enabled)
        self.text = structure.get('text', self.text)
        self.valign = VAlign(structure.get('valign', self.valign.name))
        self.image = structure.get('image')
        self.angle = structure.get('angle', self.angle)
        if 'font' in structure:
            self.font = Font()


TAG_REGISTRY = {
    'ReportTitle': ReportTitle,
    'HeaderBand': HeaderBand,
    'FooterBand': FooterBand,
    'GroupHeader': GroupHeader,
    'GroupFooter': GroupFooter,
    'PageFooter': PageFooter,
    'PageHeader': PageHeader,
    'DataBand': DataBand,
    'ChildBand': ChildBand,
}
