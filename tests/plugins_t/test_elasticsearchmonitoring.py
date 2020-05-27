from tardis.plugins.elasticsearchmonitoring import ElasticsearchMonitoring
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from ..utilities.utilities import run_async


class TestElasticsearchMonitoring(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch(
            "tardis.plugins.elasticsearchmonitoring.Configuration"
        )
        cls.mock_elasticsearch_patcher = patch(
            "tardis.plugins.elasticsearchmonitoring.Elasticsearch"
        )
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_elasticsearch = cls.mock_elasticsearch_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_elasticsearch_patcher.stop()

    @patch("tardis.plugins.elasticsearchmonitoring.logging", Mock())
    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.Plugins.ElasticsearchMonitoring._index = "index"
        self.config.Plugins.ElasticsearchMonitoring._meta = "meta"

        #  elasticsearch_inst = self.mock_elasticsearch.Elasticsearch.return_value

        self.plugin = ElasticsearchMonitoring()

    @patch("tardis.plugins.elasticsearchmonitoring.logging", Mock())
    def test_notify(self):
        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            resource_status=ResourceStatus.Booting,
            drone_uuid="test-drone",
        )
        run_async(self.plugin.async_execute, test_param)

        self.mock_elasticsearch.return_value.search.assert_called()
        self.mock_elasticsearch.return_value.create.assert_called()

        self.mock_elasticsearch.reset()
