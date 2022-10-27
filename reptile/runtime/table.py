from reptile.runtime.stream import Line, Cell, Container


class TableCell(Cell):
    colspan = 1
    rowspan = 1


class TableLine(Line):
    cell_cls = TableCell


class Table(Container):
    _prev_line = None
    _line = None

    def __init__(self):
        self._prepare()

    def _prepare(self):
        self._lines = []

    def write(self, *args):
        """
        Write a value to a cell
        :return:
        """
        if self._line is None:
            self.new_line()
        self._line.write(*args)

    def writeln(self, *args):
        self.new_line()
        self._line.write(*args)

    def new_line(self):
        self._prev_line = self._line
        self._line = TableLine()
        self._lines.append(self._line)
