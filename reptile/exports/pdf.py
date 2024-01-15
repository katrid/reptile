from PySide6.QtGui import QPainter, QFont, QGuiApplication, QPageSize, QPageLayout, QPdfWriter, QPen, QColor
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF, QSizeF, QSize, QPoint

from reptile.runtime import PreparedBand, PreparedText, PreparedImage, PreparedLine
from reptile.engines.qt import BandRenderer, TextRenderer, ImageRenderer, LineRenderer
from reptile.core.units import mm


class QReportEngine:
    app = QGuiApplication([])
    app.exit()


class PDF:
    def __init__(self, document):
        self.document = document
        self.printer = None
        self.painter = None
        self._isFirstPage = False

    def export(self, filename):
        self.printer = QPdfWriter(filename)
        self.printer.setPageMargins(QMarginsF(0, 0, 0, 0))
        self.printer.setResolution(96)
        pages = self.document.pages
        if pages:
            page = pages[0]
            self.printer.setPageSize(QPageSize(QSizeF(page.width / mm, page.height / mm), QPageSize.Millimeter))
        self.painter = QPainter()
        self.painter.setFont(QFont('Helvetica', 9))
        self.painter.begin(self.printer)
        self._isFirstPage = True
        for page in pages:
            if watermark := getattr(page, 'watermark'):
                self.draw_watermark(watermark, page)
            self.exportPage(page)
            self._isFirstPage = False
        self.painter.end()
        del self.painter
        del self.printer

    def draw_watermark(self, wm, page):
        self.painter.save()
        self.painter.setFont(QFont('Helvetica', wm.get('size', 72)))
        self.painter.rotate(wm.get('angle', 0))
        self.painter.setPen(QPen(QColor(0)))
        self.painter.setOpacity(wm.get('opacity', .3))
        self.painter.drawText(QPoint(page.width - self.painter.fontMetrics().horizontalAdvance(wm.get('text')) - (page.x * 1.5), page.height/2), wm.get('text'))
        self.painter.restore()
        self.painter.save()

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

