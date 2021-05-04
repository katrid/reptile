import sys
import os
from unittest import TestCase
import PySide2
from PySide2.QtWidgets import QApplication
from reptile import Report, DataSource, Qt
from reptile.exports import pdf


class GridTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasource = DataSource([
            {
                'id': i,
                'name': 'Product %s' % i,
                'price': i * 10.01,
                'group_name': 'Group %s' % ((i - 1) // 10 + 1),
            }
            for i in range(1, 61)
        ])
        if isinstance(PySide2.QtGui.qApp, type(None)):
            cls.app = QApplication(sys.argv)

    def test_grid(self):
        rep = Report()
        rep.default_datasource = self.datasource
        rep.load_file(os.path.join(os.path.dirname(__file__), 'test_grid.xml'))
        doc = rep.prepare()
        self.assertEqual(len(rep.pages), 1)
        page = rep.pages[0]
        band = page.bands[0]
        self.assertEqual(band.objects[2].h_align, Qt.AlignRight)
        self.assertEqual(len(doc.pages), 2)
        prepared_page = doc.pages[0]
        prepared_band = prepared_page.bands[0]
        self.assertEqual(len(prepared_page.bands), 54)
        self.assertEqual(prepared_band.objects[1].h_align, 0)
        self.assertEqual(prepared_band.objects[2].h_align, Qt.AlignRight)

    def test_grid_footer(self):
        rep = Report()
        rep.default_datasource = self.datasource
        rep.load_file(os.path.join(os.path.dirname(__file__), 'test_grid_footer.xml'))
        doc = rep.prepare()
        self.assertEqual(len(rep.pages), 1)
        page = rep.pages[0]
        band = page.bands[1]
        self.assertEqual(band.objects[1].text, 'Name')
        # self.assertEqual(len(doc.pages), 2)
        prepared_page = doc.pages[0]
        # self.assertEqual(len(prepared_page.bands), 54)
        pdf.Export(doc).export(os.path.join(os.path.dirname(__file__), 'test_grid_footer.pdf'))
