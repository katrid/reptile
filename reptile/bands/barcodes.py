import warnings
from io import BytesIO
from typing import List

from barcode import Code128, ITF
from barcode.writer import SVGWriter, ImageWriter

from reptile import EnvironmentSettings
from reptile.bands.widgets import BandObject, TAG_REGISTRY


class Barcode(BandObject):
    field: str = None
    code: str = None
    barcode_type = 'code128'
    show_text = True
    expression: str = None
    text: str = None
    _template = None
    _datasource = None

    @staticmethod
    def get_type():
        return 'Barcode'

    def load(self, data: dict):
        super().load(data)
        self.field = data.get('field')
        self._datasource = data.get('datasource')
        self.barcode_type = data.get('barcodeType')
        self.show_text = data.get('showText', True)
        self.expression = data.get('expression')
        self.text = data.get('text')

    def dump(self) -> dict:
        return {
            'type': self.get_type(),
            'name': self.name,
            'field': self.field,
            'datasource': self._datasource and self._datasource.name,
            'barcodeType': self.barcode_type,
            'showText': self.show_text,
            'left': self.left,
            'top': self.top,
            'height': self.height,
            'width': self.width,
        }

    @property
    def template(self):
        if self._template is None:
            self._template = EnvironmentSettings.env.from_string('{{ '+ self.expression + ' }}', {'this': self})
        return self._template

    def prepare(self, stream: List, context):
        from reptile.runtime import PreparedBarcode, SizeMode, PreparedImage
        from reptile.barcodes import code128

        code = None
        if self.field:
            if self._datasource:
                code = context[self.datasource_name][self.field]
            else:
                warnings.warn('Datasource not found')
        elif self.expression:
            code = self.template.render(context).strip()

        if code:
            img = PreparedBarcode() if self.barcode_type.startswith('code128') else PreparedImage()
            img.size_mode = SizeMode.STRETCH
            img.left = self.left
            img.top = self.top
            img.height = self.height
            img.width = self.width
            if self.barcode_type == 'code128' or self.barcode_type == 'code128C':
                print('barcode', code)
                img.data = code128.get_barcode(code)
            elif self.barcode_type == 'ITF-14':
                s = BytesIO()
                ITF(code, writer=ImageWriter()).write(s, options={'write_text': False, 'quiet_zone': 5})
                s.seek(0)
                img.picture = s.read()
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


TAG_REGISTRY['Barcode'] = Barcode
TAG_REGISTRY['barcode'] = Barcode
