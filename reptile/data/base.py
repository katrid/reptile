from typing import Optional, Iterable

from reptile.core import ReportObject, Report


class DataSource(ReportObject):
    _data: Optional[Iterable] = None
    _opened = False
    _report = None
    connection = None
    name: str = None

    def __init__(self, data: Iterable = None):
        self._data = data

    def open(self):
        self._opened = True

    def close(self):
        self._data = None
        self._opened = False

    @property
    def data(self) -> Iterable:
        if not self._opened:
            self.open()
        return self._data

    def set_report(self, value: Report):
        if self._report and self in self._report.pages:
            self._report.datasources.remove(self)
        self._report = value
        if value:
            value.datasources.append(self)
