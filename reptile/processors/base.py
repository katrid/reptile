from reptile.runtime.stream import ReportStream, Page, Line, Cell
from reptile.runtime.table import Table


class BaseEngine:
    def begin(self):
        pass

    def end(self):
        pass

    def from_stream(self, stream: ReportStream):
        self.begin()
        for page in stream.pages:
            self.render_page(page)
        self.end()

    def render_page(self, page: Page):
        for line in page.lines:
            if isinstance(line, Table):
                self.render_table(line)
            else:
                self.render_line(line)

    def render_line(self, line: Line):
        for cell in line.cells:
            self.render_cell(cell)

    def render_table(self, table: Table):
        for line in table._lines:
            self.render_line(line)

    def render_cell(self, cell: Cell):
        pass

    def text(self, text: str, x: int, y: int, w: int, h: int):
        """
        Draw text
        :param x:
        :param y:
        :param w:
        :param h:
        :param text:
        :return:
        """
        pass
