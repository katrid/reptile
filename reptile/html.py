from .engine import report_env


class HtmlReport:
    title: str = None
    _page = None
    params = None
    _grid = None

    def __init__(self):
        self.pages = []

    def prepare(self):
        stream = []
        context = {}
        if self.params:
            context.update(self.params)
        for page in self.pages:
            context['page'] = page
            stream.extend(page.render(context))
        return ''.join(stream)

    def from_node(self, node):
        if 'title' in node.attrib:
            self.title = node.attrib.get('title')
        for child in node:
            self.create_element(child)
        return self

    def default_datasource(self):
        return []

    def create_element(self, node):
        if node.tag == 'grid':
            el = Grid.from_node(node)
            el.page = self.page
            self.page.append(el)
            return el
        if node.tag == 'field':
            # auto create grid
            if self._grid is None:
                self._grid = Grid()
                self._grid.datasource = self.default_datasource()
                self.page.append(self._grid)
            col = self.create_column(node)
            self._grid.add_column(col)
            return col

    def create_column(self, node):
        col = GridColumn()
        col.name = node.attrib.get('name')
        col.caption = node.attrib.get('caption')
        col.css = node.attrib.get('class')
        return col

    @property
    def page(self):
        if self._page is None:
            self._page = HtmlPage(self)
            self.pages.append(self._page)
        return self._page


class HtmlPage:
    def __init__(self, report):
        self.objects: list['HtmlWidget'] = []
        self.report = report

    def render(self, context):
        stream = []
        for obj in self.objects:
            obj.render(stream, context)
        return stream

    def append(self, obj):
        self.objects.append(obj)


class HtmlWidget:
    cols = 12

    def render(self, stream, context):
        pass


class Grid(HtmlWidget):
    sql: str = None
    thead = None
    footer = None
    legend = None
    _datasource = None
    page: HtmlPage = None
    class_: str = None

    def __init__(self):
        self.columns = []

    @property
    def report(self):
        return self.page.report

    @property
    def datasource(self):
        if self._datasource is None:
            self._datasource = report_env.create_datasource(self.sql)
            self._datasource.params.assign(self.report.params)
            self._datasource.open()
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        self._datasource = value

    @classmethod
    def from_node(cls, node):
        g = cls()
        g.class_ = node.attrib.get('class')
        for child in node:
            if child.tag == 'sql':
                g.sql = child.text.replace(':', '@')
            elif child.tag == 'column':
                g.add_column(GridColumn.from_node(child))
            elif child.tag == 'thead':
                g.thead = child
            elif child.tag == 'legend':
                legend = child.text
        return g

    def add_column(self, column: 'GridColumn'):
        self.columns.append(column)

    def render(self, stream, context):
        context['data'] = self.datasource
        table = []
        div = []
        if self.legend:
            div.append(h('h5', self.legend, **{'class': 'legend'}))
        if self.thead:
            table.append(self.thead.tostring())
        else:
            table.append(
                h('thead', h('tr', *[h('th', col.caption or col.name) for col in self.columns]))
            )

        rows = []
        for rec in self.datasource:
            context['record'] = rec
            rows.append(h('tr', *[col.render(context) for col in self.columns]))

        tbody = h('tbody', *rows)
        table.append(tbody)
        table.append(h('tbody', ))
        if self.footer:
            GridFooter(self.footer).render(table, context)
        table_css = 'table table-striped table-bordered ' + (self.class_ or '')
        div.append(h('table', *table, **{'class': table_css}))
        stream.append(h('div', *div, **{'class': 'col-' + str(self.cols)}))


class GridFooter:
    def __init__(self, footer):
        self.footer = footer

    def render(self, stream, context):
        tr = []
        for child in self.footer:
            if child.tag == 'tr':
                continue
            else:
                tr.append(report_env.from_string(child.tostring()).render(context))
        stream.append(tr)


class GridColumn:
    name: str = None
    caption: str = None
    total: str = None
    foot: str = None
    _template = None
    css: str = None

    @classmethod
    def from_node(cls, node):
        col = cls()
        col.name = node.attrib.get('name')
        col.caption = node.attrib.get('caption')
        col.total = node.attrib.get('total')
        return col

    @property
    def content(self):
        return '{{ record.' + self.name + ' }}'

    @property
    def template(self):
        if self._template is None:
            print('content', self.content)
            self._template = report_env.from_string(self.content)
        return self._template

    def render(self, context):
        return h('td', self.template.render(**context))


def h(tag, *args, **kwargs):
    html = f'<{tag}'
    if kwargs:
        html += ' ' + ' '.join([f'{k}="{v}"' if v else k for k, v in kwargs.items()])
    if args:
        html += '>' + ''.join(args)
        html += f'</{tag}>'
    else:
        html += '/>'
    return html
