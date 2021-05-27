from PySide2.QtGui import QPainter, QFont, QGuiApplication, QPageSize, QPageLayout
from PySide2.QtPrintSupport import QPrinter
from PySide2.QtCore import QMarginsF, QSizeF, QSize
from PySide2.QtWidgets import QApplication
from reptile.runtime import PreparedBand, PreparedText, PreparedImage, PreparedLine
from reptile.qt import BandRenderer, TextRenderer, ImageRenderer, LineRenderer
from reptile.units import mm


class QReportEngine:
    app = QApplication([])


class PDF:
    def __init__(self, document):
        self.document = document
        self.printer = None
        self.painter = None
        self._isFirstPage = False

    def export(self, filename):
        self.printer = QPrinter()
        self.printer.setOutputFormat(QPrinter.PdfFormat)
        self.printer.setOutputFileName(filename)
        self.printer.setPageMargins(QMarginsF(0, 0, 0, 0))
        self.printer.setResolution(96)
        self.printer.setFullPage(True)
        pages = self.document['pages']
        if pages:
            page = pages[0]
            self.printer.setPageSizeMM(QSizeF(page.width / mm, page.height / mm))
        self.painter = QPainter()
        self.painter.begin(self.printer)
        self._isFirstPage = True
        for page in pages:
            self.exportPage(page)
            self._isFirstPage = False
        self.painter.end()

    def exportPage(self, page):
        if not self._isFirstPage:
            self.printer.newPage()
        for band in page.bands:
            self.exportBand(band)

    def exportBand(self, band: PreparedBand):
        BandRenderer.draw(band, self.painter)
        for obj in band.objects:
            if isinstance(obj, PreparedText):
                TextRenderer.draw(band.left, band.top, obj, self.painter)
            elif isinstance(obj, PreparedImage):
                ImageRenderer.draw(band.left, band.top, obj, self.painter)
            elif isinstance(obj, PreparedLine):
                LineRenderer.draw(band.left, band.top, obj, self.painter)

