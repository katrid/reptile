from PySide2.QtPrintSupport import QPrinter
from PySide2.QtCore import QUrl, QMarginsF
from PySide2.QtGui import QPageLayout, QPageSize
from PySide2.QtWidgets import QApplication
from PySide2.QtWebEngine import QtWebEngine
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings

from reptile.units import mm

QtWebEngine.initialize()
app = QApplication([])


def print_pdf(page: QWebEngineView, filename):
    page.page().printToPdf(
        filename, QPageLayout(
            QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(5 * mm, 5 * mm, 5 * mm, 5 * mm)
        )
    )
    page.page().pdfPrintingFinished.connect(lambda file_path, success: app.quit())


def render(html: bytes, filename: str):
    page = QWebEngineView()
    # printer = QPrinter()
    # printer.setOutputFileName('/mnt/data/test.pdf')
    page.loadFinished.connect(lambda self: print_pdf(page, filename))
    page.setHtml(html, QUrl('file://'))
    
    app.exec_()
