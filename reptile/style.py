from dataclasses import dataclass


@dataclass
class Fill:
    __slots__ = ('color1', 'color2')
    color1: int
    color2: int

    def __bool__(self):
        return bool(self.color1)


@dataclass
class Border:
    __slots__ = ('color', 'width', 'top', 'left', 'right', 'bottom')
    color: int
    width: int
    top: bool
    right: bool
    bottom: bool
    left: bool

    def __bool__(self):
        return self.color is not None


class Style:
    def __init__(self, bg_color=None):
        self.bg_color = bg_color
