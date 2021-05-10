from PySide2.QtPrintSupport import QPrinter
from PySide2.QtCore import QUrl, QMarginsF
from PySide2.QtGui import QPageLayout, QPageSize
from PySide2.QtWidgets import QApplication
from PySide2.QtWebEngine import QtWebEngine
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings

from reptile.units import mm

QtWebEngine.initialize()

app = QApplication([])


def print_pdf(page: QWebEngineView):
    page.page().printToPdf('/mnt/data/test.pdf', QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(5 * mm, 5 * mm, 5 * mm, 5 * mm)))
    # app.quit()


def render(html: bytes):
    page = QWebEngineView()
    # printer = QPrinter()
    # printer.setOutputFileName('/mnt/data/test.pdf')
    page.loadFinished.connect(lambda self: print_pdf(page))
    page.setHtml(html, QUrl('file://'))
    
    app.exec_()
