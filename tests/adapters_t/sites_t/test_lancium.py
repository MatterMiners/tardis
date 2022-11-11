from tardis.adapters.sites.lancium import LanciumAdapter

from unittest import TestCase
from unittest.mock import patch


class TestLanciumAdapter(TestCase):
    mock_config_patcher = None
    mock_lancium_api_patcher = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_config_patcher = patch("tardis.interfaces.siteadapter.Configuration")
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_lancium_api_patcher = patch(
            "tardis.adapters.sites.lancium.LanciumClient"
        )
        cls.mock_openstack_api = cls.mock_lancium_api_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_lancium_api_patcher.stop()

    def setUp(self) -> None:
        self.adapter = LanciumAdapter(machine_type="test2large", site_name="TestSite")
