import os
from unittest import TestCase
from reptile import Report


class XmlTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = [
            {
                'id': i,
                'name': f'Name {i}',
            }
            for i in range(100)
        ]

    def test_xml(self):
        pass

