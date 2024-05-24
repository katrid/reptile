import sys
import os
import time
from unittest import TestCase
from PySide6.QtGui import QPainter, QGuiApplication, QFont, QPageSize, QPageLayout, QPdfWriter, QFontDatabase
from PySide6.QtCore import QMarginsF, QSizeF, QSize, QCoreApplication
from PySide6.QtWidgets import QApplication
from reptile.bands import Report, DataBand, DataSource, Text
from reptile.exports import pdf


class EngineTestCase(TestCase):
    def test_report(self):
        app = QGuiApplication()
        print(QFontDatabase().families())
        for i in range(100):
            pdf = QPdfWriter('test.pdf')
            page = pdf.newPage()
            painter = QPainter()
            painter.begin(pdf)
            for i in range(100):
                painter.setFont(QFont('Verdana', 9))
                painter.drawText(i, 10, 'test report')
            painter.end()

    def _test_dict_datasource(self):
        rep = Report()
        page = rep.new_page()
        band = DataBand(page)
        band.datasource = DataSource([{'id': i, 'name': 'Value %s' % i} for i in range(1, 11)])
        text = Text('Line {{ line }}')
        band.add_object(text)
        text2 = Text("{{ record['id'] }} - {{ record['name'] }}")
        band.add_object(text2)
        text2.left = text.width
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        self.assertEqual(len(page.bands), 10)
        band = page.bands[-1]
        self.assertEqual(len(band.objects), 2)
        self.assertEqual(band.objects[0].text, 'Line 10')
        self.assertEqual(band.objects[1].text, '10 - Value 10')
        for i in range(100):
            pdf.PDF(doc).export(os.path.join(os.path.dirname(__file__), 'test_engine.pdf'))
