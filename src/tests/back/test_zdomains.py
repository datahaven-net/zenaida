from django.test import TestCase

from back import zdomains

class SimpleTestCase(TestCase):

    def setUp(self):
        pass

    def test_domain_is_valid(self):
        self.assertEqual(True, zdomains.is_valid('test.com'))
