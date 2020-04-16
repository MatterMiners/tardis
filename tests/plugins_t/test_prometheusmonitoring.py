from tardis.plugins.prometheusmonitoring import PrometheusMonitoring
from tardis.resources.dronestates import RequestState
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import patch

from ..utilities.utilities import run_async


class TestPrometheusMonitoring(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch(
            "tardis.plugins.prometheusmonitoring.Configuration"
        )
        cls.mock_config = cls.mock_config_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()

    @patch("tardis.plugins.prometheusmonitoring.logging", Mock())
    def setUp(self):
        self.config = self.mock_config.return_value
        self.config.Plugins.PrometheusMonitoring.addr = "127.0.0.1"
        self.config.Plugins.PrometheusMonitoring.port = 1234

        self.plugin = PrometheusMonitoring()

    @patch("tardis.plugins.prometheusmonitoring.logging", Mock())
    def test_notify(self):
        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345666",
            resource_status=ResourceStatus.Booting,
        )
        test_state = RequestState()

        run_async(self.plugin.notify, test_state, test_param)

        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 0.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345666",
            resource_status=ResourceStatus.Running,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 0.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345666",
            resource_status=ResourceStatus.Stopped,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 0.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345666",
            resource_status=ResourceStatus.Deleted,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 0.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345667",
            resource_status=ResourceStatus.Error,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 1.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345669",
            resource_status=ResourceStatus.Booting,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 1.0

        test_param = AttributeDict(
            site_name="test-site",
            machine_type="test_machine_type",
            created=datetime.now(),
            updated=datetime.now(),
            drone_uuid="12345668",
            resource_status=ResourceStatus.Error,
        )
        run_async(self.plugin.notify, test_state, test_param)
        assert self.plugin._gauges[ResourceStatus.Booting].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Running].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Stopped].get({}) == 0.0
        assert self.plugin._gauges[ResourceStatus.Deleted].get({}) == 1.0
        assert self.plugin._gauges[ResourceStatus.Error].get({}) == 2.0
