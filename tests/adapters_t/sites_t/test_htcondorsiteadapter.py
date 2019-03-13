from tardis.adapters.sites.htcondor import HTCondorSiteAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.utilities.attributedict import AttributeDict
from ...utilities.utilities import async_return
from ...utilities.utilities import mock_executor_run_command
from ...utilities.utilities import run_async

from datetime import datetime
from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

CONDOR_SUBMIT_OUTPUT = """Submitting job(s).
1 job(s) submitted to cluster 1351043."""

CONDOR_Q_OUTPUT_IDLE = """"

-- Schedd: test.etp.kit.edu : <129.11.111.111:9618?... @ 03/12/19 09:16:58
OWNER   BATCH_NAME      SUBMITTED   DONE   RUN    IDLE  TOTAL JOB_IDS
test CMD: test.sh   3/12 09:15      _      _      1      1 1351043.0

1 jobs; 0 completed, 0 removed, 1 idle, 0 running, 0 held, 0 suspended"""

CONDOR_Q_OUTPUT_RUN = """


-- Schedd: test.etp.kit.edu : <129.11.111.111:9618?... @ 03/12/19 09:23:09
OWNER   BATCH_NAME      SUBMITTED   DONE   RUN    IDLE  TOTAL JOB_IDS
test CMD: test.sh   3/12 09:15      _      1      _      1 1351043.0

1 jobs; 0 completed, 0 removed, 0 idle, 1 running, 0 held, 0 suspended"""

CONDOR_RM_OUTPUT = """"All jobs in cluster 1351043 have been marked for removal"""


class TestHTCondorSiteAdapter(TestCase):
    mock_config_patcher = None
    mock_executor_patcher = None

    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.sites.htcondor.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch('tardis.adapters.sites.htcondor.ShellExecutor')
        cls.mock_executor = cls.mock_executor_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_executor_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.MachineMetaData = self.machine_meta_data
        test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        test_site_config.executor = self.mock_executor.return_value
        test_site_config.jdl = 'submit.jdl'
        test_site_config.max_age = 10

        self.adapter = HTCondorSiteAdapter(machine_type='test2large', site_name='TestSite')

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=8, Memory='32'))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict())

    @mock_executor_run_command(stdout=CONDOR_SUBMIT_OUTPUT)
    def test_deploy_resource(self):
        response = run_async(self.adapter.deploy_resource, AttributeDict())
        self.assertEqual(response.resource_id, 1351043)
        self.assertFalse(response.created - datetime.now() > timedelta(seconds=1))
        self.assertFalse(response.updated - datetime.now() > timedelta(seconds=1))

        self.mock_executor.return_value.run_command.assert_called_with('condor_submit submit.jdl')
        self.mock_executor.reset()

    def test_machine_meta_data(self):
        self.assertEqual(self.adapter.machine_meta_data, self.machine_meta_data.test2large)

    def test_machine_type(self):
        self.assertEqual(self.adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.adapter.site_name, 'TestSite')

    def test_resource_status(self):
        run_async(self.adapter.resource_status, AttributeDict(resource_id=1351043))

    def test_stop_resource(self):
        run_async(self.adapter.stop_resource, AttributeDict(resource_id=1351043))

    def test_terminate_resource(self):
        run_async(self.adapter.terminate_resource, AttributeDict(resource_id=1351043))

    def test_exception_handling(self):
        def test_exception_handling(raise_it, catch_it):
            with self.assertRaises(catch_it):
                with self.adapter.handle_exceptions():
                    raise raise_it

        matrix = [(Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
