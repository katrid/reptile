import tempfile

from PySide6.QtGui import (
    QPainter, QFont, QGuiApplication, QPageSize, QPageLayout, QPdfWriter, QPen, QColor, QTextOption,
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF, QSizeF, QSize, QPoint, Qt, QRectF

from reptile.runtime import PreparedBand, PreparedText, PreparedImage, PreparedLine, PreparedBarcode
from reptile.engines.qt import BandRenderer, TextRenderer, ImageRenderer, LineRenderer, BarcodeRenderer
from reptile.bands import Watermark
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

    def export(self, filename) -> bytes:
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
            self.exportPage(page)
            self._isFirstPage = False
        self.painter.end()
        del self.painter
        del self.printer

    def export_bytes(self):
        with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
            self.export(tmp.name)
            return tmp.read()

    def draw_watermark(self, wm: Watermark, page):
        self.painter.save()
        if wm.font:
            self.painter.setFont(wm.font)
            self.painter.setPen(wm.font.color)
        else:
            self.painter.setFont(QFont('Helvetica', 78, QFont.Bold))
            self.painter.setPen(QPen(QColor(128, 128, 128), 1))
        self.painter.rotate(wm.angle)
        self.painter.setOpacity(wm.opacity)
        # draw text at the center of the page
        # with word wrapping
        self.painter.drawText(
            QRectF(0, 0, page.width, page.height),
            Qt.AlignCenter | Qt.TextFlag.TextWordWrap,
            wm.text,
        )

        # self.painter.drawText(
        #     QPoint(page.width - self.painter.fontMetrics().horizontalAdvance(wm.text), page.height/2),
        #     wm.text
        # )
        self.painter.restore()

    def exportPage(self, page):
        if not self._isFirstPage:
            self.printer.newPage()
        if page.watermark:
            self.draw_watermark(page.watermark, page)
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
            elif isinstance(obj, PreparedBarcode):
                BarcodeRenderer.draw(band.left, band.top, obj, self.painter)

