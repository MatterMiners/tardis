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

    def test_or_with_dict(self):
        other = {"new": 42}
        merged = self.test_dictionary | other
        self.assertIsInstance(merged, AttributeDict)
        self.assertEqual(merged["test"], 1)
        self.assertEqual(merged["another_test"], 2)
        self.assertEqual(merged["new"], 42)

    def test_or_with_dict_overwrites(self):
        other = {"test": 99}
        merged = self.test_dictionary | other
        self.assertEqual(merged["test"], 99)  # overwritten
        self.assertEqual(merged["another_test"], 2)

    def test_or_with_attributedict(self):
        other = AttributeDict(extra=123)
        merged = self.test_dictionary | other
        self.assertIsInstance(merged, AttributeDict)
        self.assertEqual(merged["test"], 1)
        self.assertEqual(merged["another_test"], 2)
        self.assertEqual(merged["extra"], 123)
