from typing import List, TYPE_CHECKING, Iterable, Optional
import datetime
from pathlib import Path
from enum import Enum

from reptile.core.base import ReportObject, Margin, BasePage
from reptile.runtime import ReportStream, PreparedPage
from reptile.core.units import mm


class ReportType(Enum):
    AUTO = 0
    TABULAR = 1
    FLUID = 2
    BAND = 3


class Report:
    title: str = None
    page_count = 0
    _pending_objects: list = None
    _level = 3
    # prepared document stream
    stream: 'ReportStream' = None

    def __init__(self, file: str | Path | dict = None, default_connection=None):
        self.pages: List[BasePage] = []
        self.datasources: List['DataSource'] = []
        # self.totals: List[Total] = []
        self.variables = {}
        self.objects = []
        # default database connection
        self.connection = default_connection
        self._context = None
        if isinstance(file, dict):
            self.load(file)

    def load(self, structure: dict):
        rep = structure['report']
        for ds in rep['dataSources']:
            if 'sql' in ds:
                datasource = self.connection.create_query(name=ds.get('name'), sql=ds['sql'])
            else:
                datasource = DataSource(ds.get('name'), data=ds['data'])
            self.register_datasource(datasource)
        for p in rep['pages']:
            page = self.new_page()
            page.load(p)

    def __getitem__(self, item):
        for page in self.pages:
            if page.name == item:
                return page

    def add_page(self, page: BasePage):
        self.pages.append(page)
        page.report = self

    def new_page(self) -> BasePage:
        from reptile.bands import Page
        # todo band report
        page = Page()
        self.add_page(page)
        return page

    def prepare(self, level=3) -> ReportStream:
        self._level = level
        self.stream = stream = ReportStream(self)
        self._pending_objects = []
        self.page_count = 0
        self._context = {
            'page_index': 0,
            'page_count': 0,
            'report': self,
            'date': datetime.date.today(),
            'time': datetime.datetime.now().strftime('%H:%M'),
            'params': self.variables,
        }
        # detect subreports
        # for obj in self.objects:
        #     if isinstance(obj, SubReport):
        #         obj.report_page = self[obj.page_name]
        # initialize context with datasource
        for ds in self.datasources:
            if ds.name:
                ds.params.assign(self.variables)
                ds.open()
                self._context[ds.name] = DataProxy(ds.data)

        for page in self.pages:
            if not page.subreport:
                page.prepare(stream.pages)

        self._context['page_count'] = self.page_count
        for txt, obj in self._pending_objects:
            obj.text = txt.render(self._context)

        self.execute()
        return stream

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
        self.datasources.append(datasource)
        self.objects.append(datasource)

    def execute(self):
        pass

    def heading(self, title: str, level=1):
        self.stream.heading(title, level)

    def h1(self, title: str):
        self.heading(title, 1)

    def h2(self, title: str):
        self.heading(title, 2)

    def h3(self, title: str):
        self.heading(title, 3)

    def h4(self, title: str):
        self.heading(title, 4)

    def h5(self, title: str):
        self.heading(title, 5)

    def h6(self, title: str):
        self.heading(title, 6)

    def table(self, data=None):
        """
        Transform the data param into a table and insert it to the stream
        :param data:
        :return:
        """
        return self.stream.page.table(data)

    def write(self, *args, colspan=None, rowspan=None):
        """
        Write cell value into current table or to the stream
        :param args:
        :param colspan:
        :param rowspan:
        :return:
        """
        self.stream.write(*args)

    def writeln(self, *args):
        self.new_line()
        self.write(*args)

    def print(self, element):
        """
        Prints an element to the report stream
        :param element:
        :return:
        """

    def new_line(self):
        """
        Created a new line into current table or report stream
        :return:
        """
        self._line = self.stream.new_line()

    def new_page(self):
        return self.stream.new_page()

    def log(self, s: str):
        """
        Log a message to report output console
        :param s:
        :return:
        """
        pass

    def render(self, engine):
        if self.stream is None:
            self.prepare()
        engine.from_stream(self.stream)
        return engine

    def read_node(self, node):
        super().read_node(node)
        if self.content:
            self.text = self.content

    def from_xml(self, xml: str):
        from lxml import etree
        self.read_node(etree.fromstring(xml))

    def from_string(self, s: str):
        if s and s[0] == '<':
            self.from_xml(s)

    def from_file(self, filename: str):
        if filename.endswith('.xml'):
            with open(filename, 'r') as f:
                self.from_string(f.read())


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

    def __len__(self):
        return len(self.data)


class _Report:
    report_type: ReportType = ReportType.AUTO
    _line = None
    _prev_line = None
    _table = None
    _page = None
    # template env
    env = None

    def __init__(self, filename_or_report: str | dict = None, title=None):
        super().__init__()
        self.filename: Optional[str] = None
        if isinstance(filename_or_report, str):
            print('load from string')
        elif isinstance(filename_or_report, dict):
            self._load(filename_or_report)
        self.totals = []
        self.datasources = {}
        self.pages = []
        self.title: str = title
        self._preparing = False

    def _load(self, structure: dict):
        rep = structure['report']
        if rep.get('type') == 'BandedReport':
            from reptile.core.bands import Page
            # banded report
            self.report_type = ReportType.BAND
            # load pages
            for p in rep['pages']:
                page = Page()
                page.load(p)

    @classmethod
    def load(cls, rep: dict):
        if isinstance(rep, dict):
            report = cls(rep)
            return report

    def _prepare(self):
        self.stream = ReportStream(self)
        self.console = []

    def prepare(self):
        self._prepare()
        stream = self.stream
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
        # for obj in self.pages:
        #     if isinstance(obj, SubReport):
        #         obj.report_page = self[obj.page_name]
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

        self.execute()
        return self.stream

    def add_page(self, page=None):
        from reptile.bands.bands import ReportPage
        if page is None:
            page = ReportPage(self)
        if page.report != self:
            page.report = self
        self.pages.append(page)
        return page


if TYPE_CHECKING:
    from reptile.runtime.stream import ReportStream
