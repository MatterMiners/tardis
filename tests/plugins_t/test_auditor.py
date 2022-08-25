from tardis.plugins.auditor import Auditor
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.resources.dronestates import AvailableState, DownState

from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from ..utilities.utilities import async_return
from ..utilities.utilities import run_async


class TestAuditor(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch("tardis.plugins.auditor.Configuration")
        cls.mock_auditorclientbuilder_patcher = patch(
            "tardis.plugins.auditor.pyauditor.AuditorClientBuilder"
        )

        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_auditorclientbuilder = cls.mock_auditorclientbuilder_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_auditorclientbuilder_patcher.stop()

    def setUp(self):
        self.address = "127.0.0.1"
        self.port = 8000
        self.timeout = 20
        self.user = "user-1"
        self.group = "group-1"
        self.site = "testsite"
        self.cores = 12
        self.memory = 100
        self.drone_uuid = "test-drone"
        self.machine_type = "test_machine_type"
        config = self.mock_config.return_value
        config.Plugins.Auditor.host = self.address
        config.Plugins.Auditor.port = self.port
        config.Plugins.Auditor.timeout = self.timeout
        config.Plugins.Auditor.user = self.user
        config.Plugins.Auditor.group = self.group
        config.Plugins.Auditor.components.test_machine_type = AttributeDict(
            Cores=AttributeDict(HEPSPEC=1.2, BENCHMARK=3.0),
            Memory=AttributeDict(BLUBB=1.4),
        )
        config.Sites = [AttributeDict(name=self.site)]
        config.testsite.MachineTypes = [self.machine_type]
        config.testsite.MachineMetaData = AttributeDict(
            test_machine_type=AttributeDict(Cores=self.cores, Memory=self.memory)
        )

        self.test_param = AttributeDict(
            site_name=self.site,
            machine_type=self.machine_type,
            created=datetime.now(),
            updated=datetime.now(),
            resource_status=ResourceStatus.Booting,
            drone_uuid=self.drone_uuid,
        )

        builder = self.mock_auditorclientbuilder.return_value
        builder = builder.address.return_value
        builder = builder.timeout.return_value
        self.client = builder.build.return_value
        self.client.add.return_value = async_return()
        self.client.update.return_value = async_return()

        self.plugin = Auditor()

    def test_notify(self):
        self.mock_auditorclientbuilder.return_value.address.assert_called_with(
            self.address,
            self.port,
        )
        self.mock_auditorclientbuilder.return_value.address.return_value.timeout.assert_called_with(
            self.timeout,
        )
        run_async(
            self.plugin.notify,
            state=AvailableState(),
            resource_attributes=self.test_param,
        )
        self.assertEqual(self.client.add.call_count, 1)
        self.assertEqual(self.client.update.call_count, 0)

        run_async(
            self.plugin.notify,
            state=DownState(),
            resource_attributes=self.test_param,
        )
        self.assertEqual(self.client.add.call_count, 1)
        self.assertEqual(self.client.update.call_count, 1)

    def test_construct_record(self):
        record = self.plugin.construct_record(resource_attributes=self.test_param)

        self.assertEqual(record.record_id, self.drone_uuid)
        self.assertEqual(record.site_id, self.site)
        self.assertEqual(record.user_id, self.user)
        self.assertEqual(record.group_id, self.group)
        self.assertEqual(len(record.components), 2)
        self.assertEqual(record.components[0].name, "Cores")
        self.assertEqual(record.components[0].amount, 12)
        self.assertEqual(len(record.components[0].scores), 2)
        self.assertEqual(record.components[0].scores[0].name, "HEPSPEC")
        self.assertEqual(record.components[0].scores[0].factor, 1.2)
        self.assertEqual(record.components[0].scores[1].name, "BENCHMARK")
        self.assertEqual(record.components[0].scores[1].factor, 3.0)
        self.assertEqual(record.components[1].name, "Memory")
        self.assertEqual(record.components[1].amount, 100)
        self.assertEqual(len(record.components[1].scores), 1)
        self.assertEqual(record.components[1].scores[0].name, "BLUBB")
        self.assertEqual(record.components[1].scores[0].factor, 1.4)
