from .bands import Page, GroupHeader, GroupFooter, DataBand
from .widgets import BandObject


class SubReport(BandObject):
    page_name: str = None
    _report_page = None
    _overlapped = False
    _x = _y = 0

    @property
    def bands(self):
        return self.report_page.bands

    @property
    def report_page(self) -> Page:
        if self.page_name:
            return self.report[self.page_name]

    @report_page.setter
    def report_page(self, value: Page):
        self.page_name = value.name
        value.subreport = self

    def prepare(self, page, context):
        # print target page
        cur_page = page
        try:
            page.x = self.left + self._x
            page.y = self.top + self._y
            for band in self.bands:
                if isinstance(band, GroupHeader):
                    page = band.prepare(page, context) or page
                elif isinstance(band, DataBand) and band.group_header is None:
                    page = band.prepare(page, context) or page
        finally:
            cur_page.x = self._x
            cur_page.y = self._y


