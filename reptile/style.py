from PySide2.QtGui import QFont, QColor
from PySide2.QtCore import QLine


class Fill:
    color_1 = None
    color_2 = None
    gradient = False

    def __bool__(self):
        return bool(self.color_1)


class Border:
    _color = None
    width = 1
    top = False
    right = False
    bottom = False
    left = False

    def __bool__(self):
        return self._color is not None

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if isinstance(value, int):
            value = QColor(value)
        self._color = value

    def get_lines(self, x1, y1, x2, y2):
        r = []
        if self.left:
            r.append(QLine(x1, y1, x1, y2))
        if self.top:
            r.append(QLine(x1, y1, x2, y1))
        if self.right:
            r.append(QLine(x2, y1, x2, y2))
        if self.bottom:
            r.append(QLine(x1, y2, x2, y2))
        return r


class Style:
    def __init__(self, bg_color=None):
        self._color = None
        self._font = QFont()
        self.fill = Fill()
        self.border = Border()
        if bg_color:
            self.fill.color_1 = bg_color

    @property
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = value

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        self._color = value

