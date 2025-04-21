from unittest import TestCase
from reptile.bands import Report, DataBand, DataSource, Text, Page, Band, Image, SizeMode
from reptile.exports import pdf


class ImageTestCase(TestCase):
    def test_img(self):
        rep = Report()
        page = rep.new_page()
        band = Band()
        page.add_band(band)
        with open('test_img.png', 'rb') as f:
            img_buf = f.read()
        # normal size mode
        img = Image()
        img.size_mode = SizeMode.NORMAL
        img.left = 0
        img.top = 0
        img.height = 100
        img.width = 100
        img.picture = img_buf
        band.add_object(img)
        img = Image()
        img.size_mode = SizeMode.AUTO
        img.left = 0
        img.top = 150
        img.height = 100
        img.width = 100
        img.picture = img_buf
        band.add_object(img)
        img = Image()
        img.size_mode = SizeMode.CENTER
        img.left = 0
        img.top = 300
        img.height = 100
        img.width = 100
        img.picture = img_buf
        band.add_object(img)
        img = Image()
        img.size_mode = SizeMode.STRETCH
        img.left = 0
        img.top = 450
        img.height = 100
        img.width = 100
        img.picture = img_buf
        band.add_object(img)
        img = Image()
        img.size_mode = SizeMode.ZOOM
        img.left = 0
        img.top = 600
        img.height = 100
        img.width = 100
        img.picture = img_buf
        band.add_object(img)

        doc = rep.prepare()
        pdf.PDF(doc).export('reports/test_img.pdf')
