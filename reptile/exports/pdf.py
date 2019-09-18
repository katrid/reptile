from PySide2.QtGui import QPainter, QPdfWriter, QFont
from PySide2.QtCore import QMarginsF


class Export:
    def __init__(self, document):
        self.document = document
        self.printer = None
        self.painter = None
        self._is_first_page = False

    def export(self, filename):
        self.printer = QPdfWriter(filename)
        self.printer.setPageMargins(QMarginsF(0, 0, 0, 0))
        self.printer.setResolution(96)
        self.painter = QPainter()
        self.painter.begin(self.printer)
        self._is_first_page = True
        for i, page in enumerate(self.document.pages):
            self.export_page(page)
            self._is_first_page = False
        self.painter.end()

    def export_page(self, page):
        if not self._is_first_page:
            self.printer.newPage()
        for band in page.bands:
            self.export_band(band)

    def export_band(self, band):
        band.draw(self.painter)
        for obj in band.objects:
            obj.draw(self.painter)

