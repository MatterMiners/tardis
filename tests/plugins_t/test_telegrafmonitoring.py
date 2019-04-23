from tardis.plugins.telegrafmonitoring import TelegrafMonitoring
from tardis.resources.dronestates import RequestState
from tardis.utilities.attributedict import AttributeDict


from unittest import TestCase
from unittest.mock import patch

from ..utilities.utilities import async_return
from ..utilities.utilities import run_async


class TestTelegrafMonitoring(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.plugins.telegrafmonitoring.Configuration')
        cls.mock_aiotelegraf_patcher = patch('tardis.plugins.telegrafmonitoring.aiotelegraf')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_aiotelegraf = cls.mock_aiotelegraf_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_aiotelegraf_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        config.Plugins.TelegrafMonitoring.host = "telegraf.test"
        config.Plugins.TelegrafMonitoring.port = 1234
        config.Plugins.TelegrafMonitoring.default_tags = {'test_tag': 'test'}

        telegraf_client = self.mock_aiotelegraf.Client.return_value
        telegraf_client.connect.return_value = async_return()
        telegraf_client.close.return_value = async_return()

        self.plugin = TelegrafMonitoring()

    def test_notify(self):
        run_async(self.plugin.notify, RequestState(), AttributeDict(test='test'))
        self.mock_aiotelegraf.Client.assert_called_with(host='telegraf.test', port=1234, tags={'test_tag': 'test'})
        self.mock_aiotelegraf.Client.return_value.connect.assert_called_with()
        self.mock_aiotelegraf.Client.return_value.metric.assert_called_with('tardis_metric',
                                                                            {'state': 'RequestState', 'test': 'test'})
        self.mock_aiotelegraf.Client.return_value.close.assert_called_with()