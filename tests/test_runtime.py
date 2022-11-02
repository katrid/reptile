from unittest import TestCase

from reptile.core.reports import Report
from reptile.engines.text import TerminalEngine


class PythonTestCase(TestCase):
    def test_stream(self):
        rep = PythonTextReport()
        prep = rep.prepare()
        self.assertEqual(len(prep.pages), 2)
        self.assertEqual(len(prep.pages[0].lines), 3)
        self.assertEqual(len(prep.pages[1].lines), 1)
        self.assertEqual([str(cell) for cell in prep.pages[0].lines[0].cells], ['Report title'])
        self.assertEqual([str(cell) for cell in prep.pages[0].lines[1].cells], ['1st line', '2nd cell', '3rd cell'])
        self.assertEqual([str(cell) for cell in prep.pages[0].lines[2].cells], ['2nd line'])

    def test_table(self):
        rep = PythonTableReport()
        text = TerminalEngine()
        rep.render(text)
        # s = text.as_text()
        # self.assertEqual(s.splitlines()[0], 'Product       Price  ')
        # print(s)
        # self.assertTrue(isinstance(prep.pages[0].lines[0], Table))


class PythonTextReport(Report):
    def execute(self):
        self.heading('Report title')
        self.write('1st line', '2nd cell')
        self.write('3rd cell')
        self.writeln('2nd line')
        self.new_page()
        self.writeln('This is a new page')


class PythonTableReport(Report):
    def execute(self):
        table = self.table()
        table.writeln('Product', 'Price')
        table.writeln('Laptop Lenovo', 999.99)
        table.writeln('Laptop Dell', 899.99)
        table.writeln('MacBook Pro', 2899.99)

        self.writeln('')

        table2 = self.table()
        table2.writeln('A', 'B', 'C', 'D', 'E', 'F', 'G')
        for i in range(1000):
            table2.writeln('#' + str(i), 999.00 + i, i, i * 999.00, i, '********', 'Cell content')
