from tardis.resources.dronestates import RequestState
from tardis.resources.poolfactory import create_composite_pool
from tardis.resources.poolfactory import str_to_state

from unittest import TestCase


class TestCompositePool(TestCase):
    def test_str_to_state(self):
        test = [{'state': 'RequestState', 'dns_name': 'test-abc123'}]
        converted_test = str_to_state(test)
        self.assertTrue(converted_test[0]['state'], RequestState)
        self.assertEqual(converted_test[0]['dns_name'], 'test-abc123')
