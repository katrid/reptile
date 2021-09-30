from itertools import groupby
from functools import partial
from collections import defaultdict

from .engine import report_env, Group


class HtmlReport:
    title: str = None
    _page = None
    params = None
    _grid = None
    connection = None

    def __init__(self):
        self.pages = []

    @classmethod
    def from_xml(cls, xml, connection=None):
        from lxml import etree
        rep = cls()
        rep.connection = connection
        xml = etree.fromstring(xml)
        rep.from_node(xml)
        return rep

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
        if node.tag == 'list':
            el = Grid.from_node(self.page, node)
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
        self.groups: list['GridGroup'] = []

    @property
    def report(self):
        return self.page.report

    @property
    def datasource(self):
        if self._datasource is None and self.sql:
            if self.report.connection:
                self._datasource = self.report.connection.create_datasource(None, self.sql)
            else:
                self._datasource = report_env.create_datasource(self.sql)
                self._datasource.params.assign(self.report.params)
            self._datasource.open()
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        self._datasource = value

    @classmethod
    def from_node(cls, page, node):
        g = cls()
        g.page = page
        g.class_ = node.attrib.get('class')
        for child in node:
            if child.tag == 'sql':
                g.sql = child.text
            elif child.tag == 'group':
                g.add_group(GridGroup.from_node(g, child))
            elif child.tag == 'column':
                g.add_column(GridColumn.from_node(child))
            elif child.tag == 'thead':
                g.thead = child
            elif child.tag == 'legend':
                legend = child.text
        return g

    def add_column(self, column: 'GridColumn'):
        self.columns.append(column)

    def add_group(self, group: 'GridGroup'):
        self.groups.append(group)

    def render(self, stream, context):
        context['data'] = self.datasource
        table = []
        div = []
        if self.legend:
            div.append(h('h5', self.legend, **{'class': 'legend'}))

        rows = []
        if self.groups:
            rows = []
            for group in self.groups:
                group.render(self.datasource.data, rows, context)
        else:
            self.render_header(table, context)
            for rec in self.datasource:
                context['record'] = rec
                rows.append(h('tr', *[col.render(context) for col in self.columns]))

        tbody = h('tbody', *rows)
        table.append(tbody)
        table.append(h('tbody'))
        if self.footer:
            GridFooter(self.footer).render(table, context)
        table_css = 'table table-striped table-bordered ' + (self.class_ or '')
        div.append(h('table', *table, **{'class': table_css}))
        stream.append(h('div', *div, **{'class': 'col-' + str(self.cols)}))

    def render_header(self, stream, context):
        if self.thead:
            stream.append(self.thead.tostring())
        else:
            stream.append(
                h('thead', h('tr', *[h('th', col.caption or col.name or '') for col in self.columns]))
            )


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


class GridGroup:
    datasource = None
    expression: str = None
    field: str = None
    text: str = None
    header = None
    footer = None
    subgroup: 'GridGroup' = None
    _template_expression = None
    _datasource_name = None
    _template = None

    def __init__(self, grid):
        self.grid = grid
        self._datasource_name = grid.datasource.name
        self._totals = defaultdict(int)


    @classmethod
    def from_node(cls, grid, node):
        group = cls(grid)
        group.expression = node.attrib.get('expression')
        group.field = node.attrib.get('field')
        group.text = node.text
        for child in node:
            if child.tag == 'header':
                group.header = GridGroupHeader.from_node(group, child)
            elif child.tag == 'footer':
                group.footer = GridGroupFooter.from_node(group, child)
            elif child.tag == 'group':
                group.subgroup = cls.from_node(grid, child)
        return group

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
                print('Error preparing expression for', self.expression)
                raise
        return self._template_expression

    @property
    def template(self):
        if not self._template:
            self._template = report_env.from_string(self.text)
        return self._template

    def eval_expression(self, row, context):
        context['record'] = row
        if self._datasource_name:
            context[self._datasource_name] = row
        return self.template_expression.render(**context)

    def render(self, datasource, stream, context):
        data = groupby(datasource, key=partial(self.eval_expression, context=context))
        line = 0
        for i, (grouper, lst) in enumerate(data):
            lst = list(lst)
            group = Group(grouper, lst, i)
            context['group'] = group
            context['records'] = lst
            if lst:
                context['record'] = lst[0]
            self.render_header(stream, context)

            if self.subgroup:
                self.subgroup.render(lst, stream, context)

            context['records'] = lst

            if not self.subgroup:
                self.grid.render_header(stream, context)
                for i, record in enumerate(lst):
                    context['record'] = record
                    context['row0'] = i
                    context['row'] = i + 1
                    line += 1
                    context['line'] = line
                    stream.append(h('tr', *[col.render(context) for col in self.grid.columns]))

            if self.footer:
                self.render_footer(stream, context)

    def render_header(self, stream, context):
        if self.header:
            self.header.render(stream, context)
        elif self.text:
            stream.append(h('tr.group-header', h('th', self.template.render(**context), colspan=len(self.grid.columns))))

    def render_footer(self, stream, context):
        if self.footer:
            self.footer.render(stream, context)


class GridGroupHeader:
    text: str = None
    node = None
    css_class = 'group-header'
    _template = None

    def __init__(self, group: GridGroup):
        self.group = group
        self._children = []

    @classmethod
    def from_node(cls, group, node):
        f = cls(group)
        if len(node):
            if hasattr(node, 'tostring'):
                if f.text:
                    f.text = node.text
                else:
                    f.text = ''.join([child.tostring() for child in node])
            else:
                from lxml import etree
                f.text = ''.join([etree.tostring(child).decode('utf-8') for child in node])
        else:
            f.text = node.text
        f.node = node
        for child in node:
            f._children.append(child)
        return f

    @property
    def template(self):
        if not self._template:
            self._template = report_env.from_string(self.text)
        return self._template

    def render(self, stream, context):
        if self.text and '<' in self.text:
            stream.append(h(f'tr.{self.css_class}', self.template.render(**context)))
        elif self.text:
            stream.append(h(f'tr.{self.css_class}', h('th', self.template.render(**context), colspan=len(self.group.grid.columns))))


class GridGroupFooter(GridGroupHeader):
    css_class = 'group-footer'


class GridColumn:
    name: str = None
    caption: str = None
    total: str = None
    foot: str = None
    _template = None
    text = None
    css: str = None

    @classmethod
    def from_node(cls, node):
        col = cls()
        col.name = node.attrib.get('name')
        col.text = node.text
        col.caption = node.attrib.get('caption')
        col.total = node.attrib.get('total')
        return col

    @property
    def content(self):
        return self.text if self.text else '{{ record.' + self.name + ' }}'

    @property
    def template(self):
        if self._template is None:
            print('content', self.content)
            self._template = report_env.from_string(self.content)
        return self._template

    def render(self, context):
        return h('td', self.template.render(**context))


def h(tag, *args, **kwargs):
    if '.' in tag:
        tag, class_ = tag.split('.', 1)
        class_ = ' '.join(class_.split('.'))
        kwargs['class'] = class_
    elif 'class_' in kwargs:
        kwargs['class'] = kwargs.pop('class_')
    html = f'<{tag}'
    if kwargs:
        html += ' ' + ' '.join([f'{k}="{v}"' if v else k for k, v in kwargs.items()])
    if args:
        html += '>' + ''.join(args)
        html += f'</{tag}>'
    else:
        html += '/>'
    return html
