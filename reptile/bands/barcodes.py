import warnings
from io import BytesIO
from typing import List

from barcode import Code128
from barcode.writer import SVGWriter

from reptile.bands.widgets import BandObject


class Barcode(BandObject):
    element_type = 'barcode'
    code: str = None
    barcode_type = 'code128'

    def prepare(self, stream: List, context):
        from barcode import Code128
        from barcode.writer import ImageWriter
        from reptile.runtime import PreparedImage, SizeMode
        img = PreparedImage()
        img.size_mode = SizeMode.CENTER
        img.left = self.left
        img.top = self.top
        img.height = self.height
        img.width = self.width
        if self.field:
            if self._datasource:
                code = context[self.datasource.name][self.field]
                if code is not None:
                    Code = None
                    if self.barcode_type == 'code128':
                        Code = Code128
                    s = BytesIO()
                    Code(code, writer=ImageWriter()).write(s, options={'write_text': False})
                    s.seek(0)
                    img.picture = s.read()
            else:
                warnings.warn('Datasource not found')
        else:
            img.picture = self.code
        stream.append(img)

    @property
    def datasource(self):
        return self._datasource

    @datasource.setter
    def datasource(self, value):
        if isinstance(value, str):
            value = self.parent.page.report.get_datasource(value)
        self._datasource = value

    def load(self, structure: dict):
        super().load(structure)
        self.field = structure.get('field')


if __name__ == '__main__':
    with open('test.svg', 'wb') as f:
        Code128('29231000033141606900559200000013951621684980', writer=SVGWriter()).write(f)
