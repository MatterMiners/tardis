from tardis.adapters.sites.slurm import SlurmAdapter
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict
from ...utilities.utilities import async_return
from ...utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch

from datetime import datetime, timedelta

import asyncio

__all__ = ['TestSlurmAdapter']

TEST_RESOURCE_STATUS_RESPONSE = '''
1390065|None assigned|PENDING
1391999|fh2n1573|TIMEOUT
1391999.batch|fh2n1573|CANCELLED
'''

TEST_RESOURCE_STATUS_RESPONSE_RUNNING = '''
1390065|fh2n1552|RUNNING
1390065.batch|fh2n1552|RUNNING
1391999|fh2n1573|TIMEOUT
1391999.batch|fh2n1573|CANCELLED
'''

TEST_RESOURCE_STATUS_RESPONSE_DEAD = '''
1390065|fh2n1552|TIMEOUT
1390065.batch|fh2n1552|CANCELLED
1391999|fh2n1573|TIMEOUT
1391999.batch|fh2n1573|CANCELLED
'''

TEST_DEPLOY_RESOURCE_RESPONSE = '''
Submitted batch job 1390065
'''


def mock_executor_run_command(stdout, stderr="", exit_code=0, raise_exception=None):
    def decorator(func):
        def wrapper(self):
            executor = self.mock_executor.return_value
            executor.run_command.return_value = async_return(return_value=AttributeDict(stdout=stdout,
                                                                                        stderr=stderr,
                                                                                        exit_code=exit_code))
            executor.run_command.side_effect = raise_exception
            func(self)
            executor.run_command.side_effect = None

        return wrapper

    return decorator


class TestSlurmAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.sites.slurm.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch('tardis.adapters.sites.slurm.ShellExecutor')
        cls.mock_executor = cls.mock_executor_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_executor_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        self.test_site_config = config.TestSite
        self.test_site_config.MachineMetaData = self.machine_meta_data
        self.test_site_config.StartupCommand = 'pilot.sh'
        self.test_site_config.StatusUpdate = 10
        self.test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        self.test_site_config.executor = self.mock_executor.return_value

        self.slurm_adapter = SlurmAdapter(machine_type='test2large', site_name='TestSite')

    def tearDown(self):
        pass

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=20, Memory='62'))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict(Partition='normal', Walltime='60'))

    @property
    def resource_attributes(self):
        return AttributeDict(machine_type='test2large',
                             site_name='TestSite',
                             remote_resource_uuid=1390065,
                             resource_status=ResourceStatus.Booting,
                             created=datetime.strptime("Wed Jan 23 2019 15:01:47", '%a %b %d %Y %H:%M:%S'),
                             updated=datetime.strptime("Wed Jan 23 2019 15:02:17", '%a %b %d %Y %H:%M:%S'),
                             drone_uuid='testsite-1390065')

    @mock_executor_run_command(TEST_DEPLOY_RESOURCE_RESPONSE)
    def test_deploy_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(created=datetime.now(), updated=datetime.now())
        return_resource_attributes = run_async(self.slurm_adapter.deploy_resource,
                                               resource_attributes=AttributeDict(machine_type='test2large',
                                                                                 site_name='TestSite'))
        if return_resource_attributes.created - expected_resource_attributes.created > timedelta(seconds=1) or \
                return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Creation time or update time wrong!")
        del expected_resource_attributes.created, expected_resource_attributes.updated, \
            return_resource_attributes.created, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)
        self.mock_executor.return_value.run_command.assert_called_with(
            'sbatch -p normal -N 1 -n 20 --mem=62gb -t 60 --export=SLURM_Walltime=60 pilot.sh')

    def test_machine_meta_data(self):
        self.assertEqual(self.slurm_adapter.machine_meta_data, self.machine_meta_data['test2large'])

    def test_machine_type(self):
        self.assertEqual(self.slurm_adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.slurm_adapter.site_name, 'TestSite')

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE)
    def test_resource_status(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now())

        return_resource_attributes = run_async(self.slurm_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE_RUNNING)
    def test_resource_status_update(self):
        self.assertEqual(self.resource_attributes["resource_status"], ResourceStatus.Booting)
        return_resource_attributes = run_async(self.slurm_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        self.assertEqual(return_resource_attributes["resource_status"], ResourceStatus.Running)
        self.assertEqual(return_resource_attributes["drone_uuid"], 'testsite-1390065')

    @mock_executor_run_command(stdout="", stderr="", exit_code=0)
    def test_stop_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.slurm_adapter.stop_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command(stdout="", stderr="", exit_code=0)
    def test_terminate_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.slurm_adapter.terminate_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command(stdout="", stderr="", exit_code=0)
    def test_terminate_dead_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.slurm_adapter.terminate_resource,
                                               resource_attributes=self.resource_attributes)
        self.assertEqual(return_resource_attributes["resource_status"], ResourceStatus.Stopped)

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE_DEAD)
    def test_dead_resource(self):
        return_resource_attributes = run_async(self.slurm_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        self.assertEqual(return_resource_attributes["resource_status"], ResourceStatus.Stopped)

    def test_resource_status_raise(self):
        # Update interval is 10 minutes, so set last update back by 2 minutes in order to execute sacct command and
        # creation date to current date
        created_timestamp = datetime.now()
        new_timestamp = datetime.now() - timedelta(minutes=2)
        self.slurm_adapter._slurm_status._last_update = new_timestamp
        with self.assertRaises(TardisResourceStatusUpdateFailed):
            response = run_async(self.slurm_adapter.resource_status,
                                 AttributeDict(resource_id=1351043, remote_resource_uuid=1351043,
                                               resource_state=ResourceStatus.Booting,
                                               created=created_timestamp))

    def test_resource_status_raise_past(self):
        # Update interval is 10 minutes, so set last update back by 11 minutes in order to execute sacct command and
        # creation date to 12 minutes ago
        past_timestamp = datetime.now() - timedelta(minutes=12)
        new_timestamp = datetime.now() - timedelta(minutes=11)
        self.slurm_adapter._slurm_status._last_update = new_timestamp
        response = run_async(self.slurm_adapter.resource_status, AttributeDict(resource_id=1390065,
                                                                               remote_resource_uuid=1351043,
                                                                               created=past_timestamp))
        self.assertEqual(response.resource_status, ResourceStatus.Stopped)

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.slurm_adapter.handle_exceptions():
                    raise to_raise

        matrix = [(asyncio.TimeoutError(), TardisTimeout),
                  (CommandExecutionFailure(message="Test", exit_code=255, stdout="Test", stderr="Test"),
                   TardisResourceStatusUpdateFailed),
                  (TardisResourceStatusUpdateFailed, TardisResourceStatusUpdateFailed),
                  (Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)
