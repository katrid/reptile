import warnings
from io import BytesIO
from typing import List

from barcode import Code128, ITF
from barcode.writer import SVGWriter

from reptile.bands.widgets import BandObject, TAG_REGISTRY

class Barcode(BandObject):
    element_type = 'barcode'
    code: str = None
    barcode_type = 'code128'
    _datasource = None

    def prepare(self, stream: List, context):
        from barcode.writer import ImageWriter
        from reptile.runtime import PreparedImage, SizeMode
        img = PreparedImage()
        img.size_mode = SizeMode.ZOOM
        img.left = self.left
        img.top = self.top
        img.height = self.height
        img.width = self.width
        if self.field:
            if self._datasource:
                code = context[self.datasource][self.field]
                if code is not None:
                    Code = None
                    if self.barcode_type == 'code128':
                        Code = Code128
                    elif self.barcode_type == 'ITF-14':
                        Code = ITF
                    s = BytesIO()
                    Code(code, writer=ImageWriter()).write(s, options={'write_text': True, 'quiet_zone': 5.0, 'dpi': 300})
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
        self._datasource = structure.get('datasource')
        self.barcode_type = structure.get('barcodeType')


TAG_REGISTRY['barcode'] = Barcode

if __name__ == '__main__':
    with open('test.svg', 'wb') as f:
        Code128('29231000033141606900559200000013951621684980', writer=SVGWriter()).write(f)
