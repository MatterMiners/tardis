from tardis.utilities.staticmapping import StaticMapping

from unittest import TestCase


class TestStaticMapping(TestCase):
    def setUp(self):
        self.test_data = {"testA": 123, "testB": "Random String"}
        self.static_map = StaticMapping(**self.test_data)

    def test_len_static_mapping(self):
        self.assertEqual(len(self.static_map), len(self.test_data))

    def test_get_item_static_mapping(self):
        self.assertEqual(self.static_map.get("testA"), self.test_data.get("testA"))
        self.assertEqual(self.static_map["testB"], self.test_data["testB"])

    def test_iter_static_mapping(self):
        static_map = StaticMapping(**self.test_data)

        for key, value in static_map.items():
            self.assertEqual(value, self.test_data.get(key))

    def test_modify_static_mapping(self):
        with self.assertRaises(TypeError):
            self.static_map["testB"] = 456
        with self.assertRaises(TypeError):
            self.static_map["testC"] = 456

    def test_eq_async_cache_map(self):
        test_static_map = StaticMapping(**self.test_data)
        self.assertTrue(self.static_map == test_static_map)

        # Test the opposite
        self.assertFalse(self.static_map != test_static_map)

        # Change the data dictionary
        test_static_map = StaticMapping(test=123)
        self.assertFalse(self.static_map == test_static_map)

        # Test different class
        self.assertFalse(self.static_map == self.test_data)
