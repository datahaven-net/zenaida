from django.test import TestCase

from back import domains

class AnimalTestCase(TestCase):

    def setUp(self):
        pass

    def test_domain_is_valid(self):
        self.assertEqual(True, domains.is_valid('test.com'))
