import sys
import os
from unittest import TestCase
from reptile import Report, DataBand, DataSource, Text
from reptile.exports import pdf


class EngineTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        if isinstance(PySide2.QtGui.qApp, type(None)):
            cls.app = QApplication(sys.argv)

    def test_engine(self):
        rep = Report()
        page = rep.add_page()
        band = DataBand(page)
        band.rows = 10
        text = Text(band)
        text.text = 'Text {{ row_index }}'
        y = page.margin.top
        by = page.bands[0].height
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        y += len(page.bands) * by
        self.assertEqual(len(page.bands), 10)
        ly = 0
        for i in range(10):
            band = page.bands[i]
            obj = band.objects[0]
            self.assertIsInstance(obj, Text)
            self.assertEqual(obj.text, 'Text %s' % i)
            ly = band.top + band.height
        self.assertEqual(y, ly)

    def test_range_data(self):
        rep = Report()
        page = rep.add_page()
        band = DataBand(page)
        band.datasource = DataSource(range(10))
        text = Text(band)
        text.text = 'Line {{ line }}'
        text2 = Text(band)
        text2.text = 'Text {{ record }}'
        text2.left = text.width
        x = page.margin.left
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        self.assertEqual(len(page.bands), 10)
        band = page.bands[0]
        self.assertEqual(len(band.objects), 2)
        self.assertEqual(band.objects[0].text, 'Line 0')
        prepared_text = band.objects[1]
        self.assertEqual(prepared_text.text, 'Text 0')
        self.assertEqual(prepared_text.left, x + text.width)

    def test_list_datasource(self):
        rep = Report()
        page = rep.add_page()
        band = DataBand(page)
        band.datasource = DataSource(['Value %s' % i for i in range(1, 11)])
        text = Text(band)
        text.text = 'Text {{ record }}'
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        self.assertEqual(len(page.bands), 10)
        band = page.bands[0]
        self.assertEqual(len(band.objects), 1)
        self.assertEqual(band.objects[0].text, 'Text Value 1')

    def test_dict_datasource(self):
        rep = Report()
        page = rep.add_page()
        band = DataBand(page)
        band.datasource = DataSource([{'id': i, 'name': 'Value %s' % i} for i in range(1, 11)])
        text = Text(band)
        text.text = 'Line {{ line }}'
        text2 = Text(band)
        text2.text = "{{ record['id'] }} - {{ record['name'] }}"
        text2.left = text.width
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        page = doc.pages[0]
        self.assertEqual(len(page.bands), 10)
        band = page.bands[-1]
        self.assertEqual(len(band.objects), 2)
        self.assertEqual(band.objects[0].text, 'Line 9')
        self.assertEqual(band.objects[1].text, '10 - Value 10')
        pdf.Export(doc).export(os.path.join(os.path.dirname(__file__), 'test_engine.pdf'))
