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
    show_text = True
    _datasource = None

    def prepare(self, stream: List, context):
        from reptile.runtime import PreparedBarcode, SizeMode, PreparedImage
        from reptile.barcodes import code128

        code = None
        if self.field:
            if self._datasource:
                code = context[self.datasource_name][self.field]
            else:
                warnings.warn('Datasource not found')

        if code:
            img = PreparedBarcode()
            img.size_mode = SizeMode.STRETCH
            img.left = self.left
            img.top = self.top
            img.height = self.height
            img.width = self.width
            if self.barcode_type == 'code128':
                img.data = code128.get_barcode(code)
            elif self.barcode_type == 'ITF-14':
                pass
            stream.append(img)

    @property
    def datasource_name(self):
        if isinstance(self._datasource, str):
            return self._datasource
        return self._datasource.name

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
        self.show_text = structure.get('showText', True)


TAG_REGISTRY['barcode'] = Barcode

if __name__ == '__main__':
    with open('test.svg', 'wb') as f:
        Code128('29231000033141606900559200000013951621684980', writer=SVGWriter()).write(f)
