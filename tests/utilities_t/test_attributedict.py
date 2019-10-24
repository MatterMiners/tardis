from tardis.utilities.attributedict import AttributeDict
from unittest import TestCase


class TestAttributeDict(TestCase):
    def setUp(self):
        self.test_dictionary = AttributeDict(test=1, another_test=2)

    def test_index_access(self):
        self.assertEqual(self.test_dictionary["test"], 1)
        self.assertEqual(self.test_dictionary["another_test"], 2)

    def test_access_via_attribute(self):
        self.assertEqual(self.test_dictionary.test, 1)
        self.assertEqual(self.test_dictionary.another_test, 2)

    def test_set_via_index(self):
        self.test_dictionary["test"] = 3
        self.assertEqual(self.test_dictionary["test"], 3)
        self.test_dictionary["yet_another_test"] = 4
        self.assertEqual(self.test_dictionary["yet_another_test"], 4)

    def test_set_via_attribute(self):
        self.test_dictionary.test = 3
        self.assertEqual(self.test_dictionary.test, 3)
        self.test_dictionary.yet_another_test = 4
        self.assertEqual(self.test_dictionary.yet_another_test, 4)

    def test_del_via_index(self):
        del self.test_dictionary["another_test"]
        with self.assertRaises(KeyError):
            self.test_dictionary["another_test"]

    def test_del_via_attribute(self):
        del self.test_dictionary.another_test
        with self.assertRaises(KeyError):
            self.test_dictionary["another_test"]

        with self.assertRaises(AttributeError):
            self.test_dictionary.another_test

        with self.assertRaises(AttributeError):
            del self.test_dictionary.another_test
