from unittest import TestCase
from reptile.bands import (
    Report, Page, GroupHeader, DataBand, Text, ReportSummary, DataSource, Band,
)


class ReportTestCase(TestCase):
    def test_nested_grouping(self):
        rep = Report()
        page = Page()
        rep.add_page(page)
        data = [
                   {'id': i, 'category': 'Category 1', 'name': 'Object %s' % i}
                   for i in range(100)
               ] + [
                   {'id': i, 'category': '2nd Category', 'name': 'Object %s' % i}
                   for i in range(100)
               ]
        datasource = DataSource(data)
        datasource.name = 'data1'
        group = GroupHeader()
        page.add_band(group)
        text_group = Text('Grouping by: {{ group.grouper }}')
        group.add_object(text_group)
        group.expression = "data1['category']"
        subgroup = GroupHeader()
        page.add_band(subgroup)
        subgroup.parent = group
        subgroup.expression = "str(data1['id'])[0]"
        text_group = Text('Sub grouping by: {{ group.grouper }}')
        subgroup.add_object(text_group)
        band = DataBand()
        page.add_band(band)
        band.datasource = datasource
        band.parent = subgroup
        band.add_object(Text('Line: {{ line }}'))
        text = Text('ID: {{ data1.id }}')
        band.add_object(text)
        text.left = 100
        text = Text('Name: {{ data1.name }} {{ data1.category }}')
        band.add_object(text)
        text.left = 200
        text = Text('relative Line: {{ row }} absolute line {{ line }} {{ even }} {{ odd }}')
        band.add_object(text)
        text.left = 11

        summary = ReportSummary(page)
        summary.add_object(Text('Total Lines: {{ line }}'))

        doc = rep.prepare()
        prepared_page = doc.pages[0]
        bands = prepared_page.bands
        prepared_text = bands[0].objects[0]
        self.assertEqual(prepared_text.text, 'Grouping by: Category 1')
        prepared_text = bands[1].objects[0]
        self.assertEqual(prepared_text.text, 'Sub grouping by: 0')
        prepared_text = bands[2].objects[1]
        self.assertEqual(prepared_text.text, 'ID: 0')
        prepared_text = bands[2].objects[2]
        self.assertEqual(prepared_text.text, 'Name: Object 0 Category 1')

    def test_simple_report(self):
        rep = Report()
        page = rep.new_page()
        band = Band()
        page.add_band(band)
        band.add_object(Text('test'))
        rep.prepare()

    def test_databand_row_count(self):
        rep = Report()
        page = rep.new_page()
        band = DataBand()
        page.add_band(band)
        band.row_count = 10
        text = Text('Line: {{ line }}')
        band.add_object(text)
        doc = rep.prepare()
        self.assertEqual(len(doc.pages), 1)
        prepared_page = doc.pages[0]
        self.assertEqual(len(prepared_page.bands), 10)
        bands = prepared_page.bands
        prepared_text = bands[0].objects[0]
        self.assertEqual(len(bands[0].objects), 1)
        self.assertEqual(prepared_text.text, 'Line: 1')
        prepared_text = bands[1].objects[0]
        self.assertEqual(prepared_text.text, 'Line: 2')
        prepared_text = bands[-1].objects[0]
        self.assertEqual(prepared_text.text, 'Line: 10')
        self.assertEqual(len(bands), 10)

    def test_databand_datasource(self):
        rep = Report()
        page = rep.new_page()
        datasource = DataSource([{'id': i, 'name': 'Object %s' % i} for i in range(10)])
        datasource.name = 'data1'
        band = DataBand()
        page.add_band(band)
        band.datasource = datasource
        band.add_object(Text('Line: {{ line }}'))
        text = Text('ID: {{ data1.id }}')
        band.add_object(text)
        text.left = 100
        text = Text('Name: {{ data1.name }}')
        band.add_object(text)
        text.left = 200
        doc = rep.prepare()
        prepared_page = doc.pages[0]
        bands = prepared_page.bands
        prepared_text = bands[0].objects[0]
        self.assertEqual(prepared_text.text, 'Line: 1')
        prepared_text = bands[0].objects[1]
        self.assertEqual(prepared_text.text, 'ID: 0')
        prepared_text = bands[0].objects[2]
        self.assertEqual(prepared_text.text, 'Name: Object 0')

    def test_group_header(self):
        rep = Report()
        page = rep.new_page()
        datasource = DataSource([{'id': i, 'name': 'Object %s' % i} for i in range(100)])
        datasource.name = 'data1'
        group = GroupHeader()
        page.add_band(group)
        text_group = Text('Grouping by: {{ group.grouper }}')
        group.add_object(text_group)
        group.expression = "str(data1['id'])[0]"
        band = DataBand()
        page.add_band(band)
        # group.children.append(band)
        band.datasource = datasource
        band.group_header = group
        group.band = band
        band.add_object(Text('Line: {{ line }}'))
        text = Text('ID: {{ data1.id }}')
        text.left = 100
        band.add_object(text)
        text = Text('Name: {{ data1.name }}')
        text.left = 200
        band.add_object(text)
        doc = rep.prepare()
        prepared_page = doc.pages[0]
        bands = prepared_page.bands
        prepared_text = bands[0].objects[0]
        self.assertEqual(prepared_text.text, 'Grouping by: 0')
        prepared_text = bands[1].objects[0]
        self.assertEqual(prepared_text.text, 'Line: 1')
        prepared_text = bands[1].objects[1]
        self.assertEqual(prepared_text.text, 'ID: 0')
        prepared_text = bands[1].objects[2]
        self.assertEqual(prepared_text.text, 'Name: Object 0')
        self.assertEqual(bands[3].objects[1].text, 'ID: 1')
        self.assertEqual(bands[4].objects[0].text, 'Grouping by: 2')
        self.assertEqual(bands[11].objects[2].text, 'Name: Object 5')
        self.assertEqual(bands[-1].objects[2].text, 'Name: Object 15')
        self.assertEqual(doc.pages[-1].bands[-1].objects[1].text, 'ID: 99')
