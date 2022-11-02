from reptile.runtime.stream import Line, Cell
from reptile.runtime.table import Table
from .base import BaseEngine

PAGE_WIDTH = 220


class TextSeparatedEngine(BaseEngine):
    separator = '\t'
    page_width = PAGE_WIDTH
    _output: list[str]

    def begin(self):
        self._output = []

    def render_line(self, line: Line, widths=None):
        cells = [self.render_cell(cell) for cell in line.cells]
        if widths:
            self._output.append(self.separator.join([self.render_cell(cell).ljust(widths[i]) for i, cell in cells]))
        else:
            self._output.append(self.separator.join(cells))

    def render_cell(self, cell: Cell):
        return cell.as_text()

    def as_text(self):
        return '\n'.join([line for line in self._output])


class TextEngine(TextSeparatedEngine):
    separator = ' '

    def render_table(self, table: Table):
        widths = None
        lines = [[self.render_cell(cell) for cell in line.cells] for line in table._lines]
        if lines:
            widths = [0 for c in lines[0]]
        for line in lines:
            for i, cell in enumerate(line):
                widths[i] = max(widths[i], len(cell))
        for i, line in enumerate(lines):
            if i == 1:
                self._output.append(self.separator.join(['-' * widths[i] for i, cell in enumerate(line)]))
            if widths:
                s = self.separator.join([cell.ljust(widths[i]) for i, cell in enumerate(line)])
            else:
                s = self.separator.join(line)
            self._output.append(s)

    def render_cell(self, cell: Cell):
        return cell.as_text()

    def as_text(self):
        return '\n'.join([line for line in self._output])


class TerminalEngine(TextEngine):
    HEADER = '\033[95m'
    ENDC = '\033[0m'

    def render_table(self, table: Table):
        widths = None
        lines = [[self.render_cell(cell) for cell in line.cells] for line in table._lines]
        if lines:
            widths = [0 for c in lines[0]]
        for line in lines:
            for i, cell in enumerate(line):
                widths[i] = max(widths[i], len(cell))
        for i, line in enumerate(lines):
            if i == 1:
                self._output.append(
                    self.HEADER + self.separator.join(['-' * widths[i] for i, cell in enumerate(line)]) + self.ENDC
                )
            if widths:
                s = self.separator.join([cell.ljust(widths[i]) for i, cell in enumerate(line)])
            else:
                s = self.separator.join(line)

            if i == 0:
                s = self.HEADER + s + self.ENDC
            self._output.append(s)

    def end(self):
        print('\n'.join(self._output))


class RichTerminalEngine(TextEngine):
    def __init__(self):
        from rich.console import Console
        self.console = Console()

    def render_table(self, table: Table):
        import rich.table
        ot = rich.table.Table(show_header=True, header_style='magenta')
        for i, line in enumerate(table._lines):
            if i == 0:
                for cell in line:
                    ot.add_column(cell.value)
            else:
                ot.add_row(*[self.render_cell(cell) for cell in line.cells])
        self.console.print(ot)
