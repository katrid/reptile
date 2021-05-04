from unittest import TestCase
from reptile.engine import *


class ReportTestCase(TestCase):
    def test_nested_grouping(self):
        rep = Report()
        page = rep.new_page()
        data = [{'id': i, 'category': 'Category 1', 'name': 'Object %s' % i} for i in range(100)] + [{'id': i, 'category': '2nd Category', 'name': 'Object %s' % i} for i in range(100)]
        datasource = DataSource('data1', data)
        group = GroupHeader(page)
        text_group = Text('Grouping by: {{ group.grouper }}', group)
        group.expression = "data1['category']"
        subgroup = GroupHeader(page)
        subgroup.parent = group
        subgroup.expression = "str(data1['id'])[0]"
        text_group = Text('Sub grouping by: {{ group.grouper }}', subgroup)
        band = DataBand(page)
        band.datasource = datasource
        band.parent = subgroup
        Text('Line: {{ line }}', band)
        text = Text('ID: {{ data1.id }}', band)
        text.left = 100
        text = Text('Name: {{ data1.name }} {{ data1.category }}', band)
        text.left = 200
        text = Text('relative Line: {{ row }} absolute line {{ line }} {{ even }} {{ odd }}', band)
        text.left = 11

        summary = ReportSummary(page)
        Text('Total Lines: {{ line }}', summary)

        doc = rep.prepare()
        prepared_page = doc['pages'][0]
        bands = prepared_page['bands']
        prepared_text = bands[0]['objects'][0]
        self.assertEqual(prepared_text['text'], 'Grouping by: Category 1')
        prepared_text = bands[1]['objects'][0]
        self.assertEqual(prepared_text['text'], 'Sub grouping by: 0')
        prepared_text = bands[2]['objects'][1]
        self.assertEqual(prepared_text['text'], 'ID: 0')
        prepared_text = bands[2]['objects'][2]
        self.assertEqual(prepared_text['text'], 'Name: Object 0 Category 1')
        print(doc['pages'][0]['bands'][-1])

    # def test_simple_report(self):
    #     rep = Report()
    #     page = rep.new_page()
    #     band = Band(page)
    #     text = Text('test', band)
    #     rep.prepare()
    #
    # def test_databand_row_count(self):
    #     rep = Report()
    #     page = rep.new_page()
    #     band = DataBand(page)
    #     band.row_count = 10
    #     text = Text('Line: {{ line }}', band)
    #     doc = rep.prepare()
    #     prepared_page = doc['pages'][0]
    #     bands = prepared_page['bands']
    #     prepared_text = bands[0]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Line: 1')
    #     prepared_text = bands[1]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Line: 2')
    #     prepared_text = bands[-1]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Line: 10')
    #     self.assertEqual(len(bands), 10)
    #
    # def test_databand_datasource(self):
    #     rep = Report()
    #     page = rep.new_page()
    #     datasource = DataSource('data1', [{'id': i, 'name': 'Object %s' % i} for i in range(10)])
    #     band = DataBand(page)
    #     band.datasource = datasource
    #     Text('Line: {{ line }}', band)
    #     text = Text('ID: {{ data1.id }}', band)
    #     text.left = 100
    #     text = Text('Name: {{ data1.name }}', band)
    #     text.left = 200
    #     doc = rep.prepare()
    #     prepared_page = doc['pages'][0]
    #     bands = prepared_page['bands']
    #     prepared_text = bands[0]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Line: 1')
    #     prepared_text = bands[0]['objects'][1]
    #     self.assertEqual(prepared_text['text'], 'ID: 0')
    #     prepared_text = bands[0]['objects'][2]
    #     self.assertEqual(prepared_text['text'], 'Name: Object 0')
    #
    # def test_group_header(self):
    #     rep = Report()
    #     page = rep.new_page()
    #     datasource = DataSource('data1', [{'id': i, 'name': 'Object %s' % i} for i in range(100)])
    #     group = GroupHeader(page)
    #     text_group = Text('Grouping by: {{ group.grouper }}', group)
    #     group.condition = "str(data1['id'])[0]"
    #     band = DataBand(page)
    #     band.datasource = datasource
    #     band.parent = group
    #     Text('Line: {{ line }}', band)
    #     text = Text('ID: {{ data1.id }}', band)
    #     text.left = 100
    #     text = Text('Name: {{ data1.name }}', band)
    #     text.left = 200
    #     doc = rep.prepare()
    #     prepared_page = doc['pages'][0]
    #     bands = prepared_page['bands']
    #     prepared_text = bands[0]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Grouping by: 0')
    #     prepared_text = bands[1]['objects'][0]
    #     self.assertEqual(prepared_text['text'], 'Line: 1')
    #     prepared_text = bands[1]['objects'][1]
    #     self.assertEqual(prepared_text['text'], 'ID: 0')
    #     prepared_text = bands[1]['objects'][2]
    #     self.assertEqual(prepared_text['text'], 'Name: Object 0')

