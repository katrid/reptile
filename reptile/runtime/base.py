from typing import List, TYPE_CHECKING

from reptile.core import Report


class Document:
    """
    Prepared report document.
    """
    __slots__ = ('report', 'pages', 'level')

    def __init__(self, report, level=3):
        self.report: 'Report' = report
        self.pages: List[PreparedPage] = []
        self.level = level

    def add_page(self):
        """
        Add a prepared page to the document
        :return:
        """
        pass
        # page = PreparedPage()
        # self.pages.append(page)
        # return page

    def dump(self) -> dict:
        """
        Dump prepared report to dict
        :return:
        """
        return {
            'pages': [p.dump() for p in self.pages],
            'level': self.level,
        }


class PreparedPage:
    __slots__ = ('height', 'width', 'bands', 'index', 'margin', 'x', 'y', 'ay')

    def __init__(self, height, width, margin=None):
        self.height = height
        self.width = width
        if margin:
            self.y = margin.top
            self.ay = height - margin.bottom
            self.x = margin.left
        self.bands: List[PreparedBand] = []
        self.margin = margin

    def add_band(self, left, top, width, height):
        band = PreparedBand(left, top, width, height)
        self.bands.append(band)
        return band

    def dump(self) -> dict:
        return {
            'bands': [b.dump() for b in self.bands]
        }


class PreparedText:
    __slots__ = (
        'left', 'top', 'height', 'width', 'allow_tags', 'text', 'font_name', 'font_size', 'font_bold', 'font_italic',
        'background', 'brush_style', 'valign', 'halign', 'border', 'word_wrap', 'can_grow', 'error',
    )

    def __init__(self, text=None, left=0, top=0):
        self.text = text
        self.left = left
        self.top = top
        self.width = None
        self.height = 0
        self.font_bold = False
        self.font_italic = False
        self.font_name = 'Helvetica'
        self.font_size = 9
        self.background = None
        self.error = False

    def dump(self):
        return {
            'left': self.left,
            'top': self.top,
            'height': self.height,
            'width': self.width,
            'text': self.text,
            'fontSize': self.font_size,
            'fontName': self.font_name,
            'error': self.error,
        }


class PreparedImage:
    __slots__ = ('picture', 'left', 'top', 'height', 'width')

    def __init__(self):
        self.picture = None
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0


class PreparedLine:
    __slots__ = ('left', 'top', 'height', 'width', 'direction', 'line_width', 'color', 'style')

    def __init__(self):
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.line_width = 1
        self.direction = 0
        self.color = 0
        self.style = 0
