import json
import unittest
from reptile.bands import Report, Page, Band, Text


class CoreTestCase(unittest.TestCase):
    def test_simple_report(self):
        for i in range(100):
            rep = Report()
            page = Page()
            rep.add_page(page)
            page.height = 400
            page.margin.left = page.margin.top = page.margin.bottom = page.margin.right = 0
            self.assertEqual(len(rep.pages), 1)
            band = Band()
            band.height = 40
            page.add_band(band)
            band = Band()
            band.height = 40
            page.add_band(band)
            self.assertEqual(len(page.bands), 2)
            text = Text('Text object 1')
            band.add_object(text)
            text = Text('Text object 2')
            text.left = 130
            band.add_object(text)
            for i in range(100):
                band = Band()
                band.height = 40
                page.add_band(band)
                band.add_object(Text(f'Text object {i}'))
            # data process only (level 1)
            doc = rep.prepare(1)
            self.assertEqual(len(doc.pages), 1)
            self.assertEqual(len(doc.pages[0].bands), 102)
            self.assertEqual(len(doc.pages[0].bands[1].objects), 2)
            self.assertEqual(doc.pages[0].bands[1].objects[0].text, 'Text object 1')
            prepared_text = doc.pages[0].bands[1].objects[1]
            self.assertEqual(prepared_text.text, 'Text object 2')
            prepared_text = doc.pages[0].bands[-1].objects[0]
            self.assertEqual(prepared_text.text, 'Text object 99')
            # dump the prepared report to json
            rep_dict = doc.dump()
            self.assertEqual(len(rep_dict['pages']), 1)
            self.assertEqual(rep_dict['level'], 1)
            # full render (level 3 default)
            doc = rep.prepare()
            self.assertEqual(len(doc.pages), 11)
            rep_dict = doc.dump()
            self.assertEqual(rep_dict['level'], 3)
            self.assertEqual(len(rep_dict['pages']), 11)
            # test json dump
            json.dumps(rep_dict)

    def test_advanced_text(self):
        text = Text('Text object 1')
        text.height = 400
        text.width = 400
        text.auto_size = True
        text.can_grow = True
        text.can_shrink = True
        new_text = text.process({})


if __name__ == '__main__':
    unittest.main()
