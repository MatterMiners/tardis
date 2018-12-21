from tardis.resources.dronestates import RequestState
from tardis.resources.poolfactory import create_composite_pool
from tardis.resources.poolfactory import load_plugins
from tardis.resources.poolfactory import str_to_state
from tardis.utilities.attributedict import AttributeDict

from unittest import TestCase
from unittest.mock import patch


class TestPoolFactory(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.resources.poolfactory.Configuration')
        cls.mock_sqliteregistry_patcher = patch('tardis.plugins.sqliteregistry.SqliteRegistry')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_sqliteregistry = cls.mock_sqliteregistry_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_sqliteregistry_patcher.stop()

    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.Plugins = AttributeDict(SqliteRegistry=AttributeDict(db_file='test.db'))

    def test_str_to_state(self):
        test = [{'state': 'RequestState', 'dns_name': 'test-abc123'}]
        converted_test = str_to_state(test)
        self.assertTrue(converted_test[0]['state'], RequestState)
        self.assertEqual(converted_test[0]['dns_name'], 'test-abc123')

    def test_load_plugins(self):
        self.assertEqual(load_plugins(), {'SqliteRegistry': self.mock_sqliteregistry()})

        self.mock_config.side_effect = AttributeError
        self.assertEqual(load_plugins(), {})
        self.mock_config.side_effect = None
