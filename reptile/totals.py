from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from reptile.engine import Report


class Total:
    name = None
    expression = None
    total_type = 'sum'
    _band = None
    _print_on_band = None
    value = 0

    def __init__(self, report: Report):
        self.report = report
        self.report.totals.append(self)

    def compute(self, context):
        if self.total_type == 'sum':
            assert self.expression
            val = eval(self.expression, {}, context)
            self.value += val
        else:
            self.value += 1
        return self.value

    @property
    def band(self):
        return self._band

    @band.setter
    def band(self, value):
        self._band = value
        self._band.totals.append(self)

    @property
    def print_on_band(self):
        return self._print_on_band

    @print_on_band.setter
    def print_on_band(self, value):
        self._print_on_band = value
        self._print_on_band.reset_totals.append(self)


