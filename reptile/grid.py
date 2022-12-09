from typing import Optional
from reptile.bands import (
    ReportObject, Page, GroupHeader, GroupFooter, DataBand,
    HeaderBand, Footer as FooterBand, Text,
)
from reptile.style import Style


class Grid(ReportObject):
    def __init__(self, parent=None, datasource=None):
        super().__init__(parent)
        self._datasource = datasource
        self.header: Optional[HeaderBand] = None
        self.footer: Optional[FooterBand] = None
        self.master: Optional[DataBand] = None
        self.group_header: Optional[GroupHeader] = None
        self.group_footer: Optional[GroupFooter] = None
        self._datasource_name: Optional[str] = None
        self.even_style = None

    def init(self, page: Page):
        # init the report style
        page.report.styles['even'] = Style(bg_color=14740725)
        has_total = False
        if self._datasource is None:
            self._datasource = self.report.default_datasource
        self.master = DataBand()
        self.master.page = page
        self.master.even_style = 'even'
        fields = []
        cols = 0
        group = None
        for child in self.objects:
            if isinstance(child, Group):
                child.init(page)
                group = child
            elif isinstance(child, HeaderBand):
                self.header = child
            elif isinstance(child, FooterBand):
                self.footer = child
            elif isinstance(child, Field):
                child.init()
                cols += child.cols
                fields.append(child)
                if child.total:
                    has_total = True

        if group:
            page.add_band(group.header)
            group.header.add_band(self.master)
            group.header.add_band(group.footer)
            group.header.footer = group.footer

        # auto create header and footer if needed
        if self.header is None:
            self.header = HeaderBand(page)
            self.header.report = self.report
            self.master.header = self.header
        self.master.add_band(self.header)

        if not group:
            page.add_band(self.master)

        if has_total and self.footer is None:
            self.footer = FooterBand()
            self.master.add_band(self.footer)
        self.master.datasource = self._datasource

        colw = page.client_width / cols
        x = 0
        for field in fields:
            field.width = colw * field.cols
            field.left = x
            self.header.add_object(field.header)
            if self.footer:
                self.footer.add_object(field.footer)
            self.master.add_object(field.label)
            x += field.width

    @property
    def datasource(self):
        if not self.datasource_name:
            return self.report.default_datasource
        return self.report.datasources[self.datasource_name]


class Group(ReportObject):
    header = None
    footer = None
    field = None

    def init(self, page: Page):
        for child in self.objects:
            if isinstance(child, GroupHeader):
                self.header = child
                self.header.field = self.field
            elif isinstance(child, GroupFooter):
                self.footer = child

    def create_element(self, child):
        tag = child.tag.lower()
        if tag == 'header':
            obj = GroupHeader()
            return obj
        elif tag == 'footer':
            obj = GroupFooter()
            return obj
        else:
            return super().create_element(child)


class Field(ReportObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name: Optional[str] = None
        self.caption: Optional[str] = None
        self.text: Optional[str] = None
        self.total: Optional[str] = None
        self.data_type: Optional[str] = None
        self.header: Optional[Text] = None
        self.footer: Optional[Text] = None
        self.label: Optional[Text] = None
        self.h_align = None
        self.v_align = None
        self._cols = 1

    def init(self):
        text = None
        if self.name:
            text = '{{ record.%s }}' % self.name
        else:
            text = self.text
        self.label = Text()
        self.label.h_align = self.h_align or self.label.h_align
        self.label.v_align = self.v_align or self.label.v_align
        self.label.text = text
        self.header = Text()
        self.header.text = self.caption if self.caption is not None else self.name
        self.header.font.setBold(True)
        self.header.h_align = self.h_align or self.header.h_align
        self.header.v_align = self.v_align or self.header.v_align
        self.footer = Text()
        self.footer.h_align = self.h_align or self.footer.h_align
        self.footer.v_align = self.v_align or self.footer.v_align
        self.footer.font.setBold(True)
        if self.total:
            if "'" in self.total:
                self.footer.text = self.total
            else:
                self.footer.text = '{{ %s(records["%s"]) }}' % (self.total, self.name)

    @property
    def cols(self):
        return self._cols

    @cols.setter
    def cols(self, value):
        if isinstance(value, str):
            value = float(value)
        self._cols = value

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        self._width = value
        self.footer.width = value
        self.header.width = value
        self.label.width = value

    @property
    def left(self):
        return self._left

    @left.setter
    def left(self, value):
        self._left = value
        self.footer.left = value
        self.header.left = value
        self.label.left = value

    def read_xml(self, node):
        super().read_xml(node)
        text = node.text
        if text:
            self.text = text.strip()

REGISTRY = {}

REGISTRY.update({
    'grid': Grid,
    'field': Field,
    'group': Group,
})
