from typing import List, TYPE_CHECKING


class Document:
    """
    Prepared report document.
    """
    __slots__ = ('report', 'pages')

    def __init__(self, report):
        self.report: 'Report' = report
        self.pages: List[PreparedPage] = []

    def add_page(self):
        pass
        # page = PreparedPage()
        # self.pages.append(page)
        # return page


class PreparedPage:
    __slots__ = ('height', 'width', 'bands', 'index', 'margin', 'x', 'y', 'ay')

    def __init__(self, height, width, margin):
        self.height = height
        self.width = width
        self.y = margin.top
        self.ay = height - margin.bottom
        self.x = margin.left
        self.bands: List[PreparedBand] = []

    def add_band(self):
        band = PreparedBand()
        self.bands.append(band)
        return band


class PreparedBand:
    __slots__ = ('left', 'top', 'height', 'width', 'bottom', 'band_type', 'objects', 'fill')

    def __init__(self):
        self.fill = None
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.bottom = 0

    def setPage(self, page: PreparedPage):
        self.top = page.y
        self.bottom = self.top + self.height


class PreparedText:
    __slots__ = (
        'left', 'top', 'height', 'width', 'allowTags', 'text', 'fontName', 'fontSize', 'fontBold', 'fontItalic',
        'backColor', 'brushStyle', 'vAlign', 'hAlign', 'border', 'wordWrap', 'canGrow',
    )


class PreparedImage:
    __slots__ = ('picture', 'left', 'top', 'height', 'width')

    def __init__(self):
        self.picture = None
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0


class PreparedLine:
    __slots__ = ('left', 'top', 'height', 'width', 'size')

    def __init__(self):
        self.left = 0
        self.top = 0
        self.height = 0
        self.width = 0
        self.size = 0


if TYPE_CHECKING:
    from .engine import Report
