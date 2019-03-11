from tardis.adapters.sites.moab import MoabAdapter
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict
from tests.utilities.utilities import async_return
from tests.utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch

from datetime import datetime, timedelta

import asyncio
import asyncssh

__all__ = ['TestMoabAdapter']

TEST_RESOURCE_STATUS_RESPONSE = '''
job 4761849

AName: hostname
State: Idle
Creds:  user:abc1234  group:abcdef  account:ab12cd34
WallTime:   00:00:00 of 2:00:00:00
SubmitTime: Wed Jan 23 15:01:47
  (Time Queued  Total: 00:00:26  Eligible: 00:00:26)

TemplateSets:  DEFAULT
Total Requested Tasks: 20

Req[0]  TaskCount: 20  Partition: ALL
Dedicated Resources Per Task: PROCS: 1  MEM: 6144M


SystemID:   Moab
SystemJID:  4761849
Notification Events: JobFail

IWD:            $HOME
SubmitDir:      $HOME
Executable:     /usr/bin/hostname

BypassCount:    1
Flags:          FSVIOLATION,GLOBALQUEUE,JOINSTDERRTOSTDOUT
Attr:           FSVIOLATION
StartPriority:  -20731
IterationJobRank: 1034
PE:             21.28

'''

TEST_RESOURCE_STATUS_RESPONSE_RUNNING = '''
job 4761849

AName: hostname
State: Running 
Creds:  user:abc1234  group:abcdef  account:ab12cd34
WallTime:   9:23:52 of 2:00:00:00
SubmitTime: Wed Jan 23 15:01:47
  (Time Queued  Total: 00:31:00  Eligible: 00:00:26)

StartTime: Wed Jan 23 15:31:47
TemplateSets:  DEFAULT
Total Requested Tasks: 20

Req[0]  TaskCount: 20  Partition: ALL
Dedicated Resources Per Task: PROCS: 1  MEM: 6144M
NodeSet=FIRSTOF:FEATURE:[NONE]

Allocated Nodes:
[n4310.nemo.privat:20]
Applied Nodeset: OPA431STOF:FEATURE:[NONE]


SystemID:   Moab
SystemJID:  4761849
Notification Events: JobFail

IWD:            $HOME
SubmitDir:      $HOME
Executable:     /usr/bin/hostname

StartCount:     1
BypassCount:    1
Flags:          FSVIOLATION,GLOBALQUEUE,JOINSTDERRTOSTDOUT
Attr:           FSVIOLATION
StartPriority:  -20731
IterationJobRank: 1034
PE:             21.28
Reservation '4932931' (-9:25:13 -> 1:14:34:47  Duration: 2:00:00:00

'''

TEST_DEPLOY_RESOURCE_RESPONSE = '''

4761849
'''

TEST_TERMINATE_RESOURCE_RESPONSE = '''

job '4761849' cancelled

'''

TEST_TIMEOUT_RESPONSE = '''
ERROR:  client timed out after 30 seconds (hostname:port=mg1.nemo.privat:42559)
'''

TEST_TERMINATE_DEAD_RESOURCE_RESPONSE = '''
ERROR:  invalid job specified (4761849)

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


class TestMoabAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapters.sites.moab.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_executor_patcher = patch('tardis.adapters.sites.moab.ShellExecutor')
        cls.mock_executor = cls.mock_executor_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_executor_patcher.stop()

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.MachineMetaData = self.machine_meta_data
        test_site_config.StartupCommand = 'startVM.py'
        test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        test_site_config.executor = self.mock_executor.return_value

        self.moab_adapter = MoabAdapter(machine_type='test2large', site_name='TestSite')

    def tearDown(self):
        pass

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=128, Memory='120'))

    @property
    def machine_type_configuration(self):
        return AttributeDict(test2large=AttributeDict(NodeType='1:ppn=20', Walltime='02:00:00:00'))

    @property
    def resource_attributes(self):
        return AttributeDict(machine_type='test2large',
                             site_name='TestSite',
                             resource_id=4761849,
                             resource_status=ResourceStatus.Booting,
                             created=datetime.strptime("Wed Jan 23 2019 15:01:47", '%a %b %d %Y %H:%M:%S'),
                             updated=datetime.strptime("Wed Jan 23 2019 15:02:17", '%a %b %d %Y %H:%M:%S'),
                             dns_name='testsite-4761849')

    @mock_executor_run_command(TEST_DEPLOY_RESOURCE_RESPONSE)
    def test_deploy_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(created=datetime.now(), updated=datetime.now())
        return_resource_attributes = run_async(self.moab_adapter.deploy_resource,
                                               resource_attributes=AttributeDict(machine_type='test2large',
                                                                                 site_name='TestSite'))
        if return_resource_attributes.created - expected_resource_attributes.created > timedelta(seconds=1) or \
                return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Creation time or update time wrong!")
        del expected_resource_attributes.created, expected_resource_attributes.updated, \
            return_resource_attributes.created, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)
        self.mock_executor.return_value.run_command.assert_called_with(
            'msub -j oe -m p -l walltime=02:00:00:00,mem=120gb,nodes=1:ppn=20 startVM.py')

    def test_machine_meta_data(self):
        self.assertEqual(self.moab_adapter.machine_meta_data, self.machine_meta_data['test2large'])

    def test_machine_type(self):
        self.assertEqual(self.moab_adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.moab_adapter.site_name, 'TestSite')

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE)
    def test_resource_status(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now())
        return_resource_attributes = run_async(self.moab_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command(TEST_RESOURCE_STATUS_RESPONSE_RUNNING)
    def test_resource_status_update(self):
        self.assertEqual(self.resource_attributes["resource_status"], ResourceStatus.Booting)
        return_resource_attributes = run_async(self.moab_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        self.assertEqual(return_resource_attributes["resource_status"], ResourceStatus.Running)

    @mock_executor_run_command(TEST_TERMINATE_RESOURCE_RESPONSE)
    def test_stop_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.moab_adapter.stop_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command(TEST_TERMINATE_RESOURCE_RESPONSE)
    def test_terminate_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.moab_adapter.terminate_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_executor_run_command("", stderr=TEST_TERMINATE_DEAD_RESOURCE_RESPONSE, exit_code=1,
                               raise_exception=CommandExecutionFailure(message='Test',
                                                                       stdout="",
                                                                       stderr=TEST_TERMINATE_DEAD_RESOURCE_RESPONSE,
                                                                       exit_code=1))
    def test_terminate_dead_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.moab_adapter.terminate_resource,
                                               resource_attributes=self.resource_attributes)
        self.assertEqual(return_resource_attributes["resource_status"], ResourceStatus.Stopped)

    @mock_executor_run_command("", exit_code=2, raise_exception=CommandExecutionFailure(message='Test',
                                                                                        stdout="",
                                                                                        stderr="",
                                                                                        exit_code=2))
    def test_terminate_resource_error(self):
        with self.assertRaises(CommandExecutionFailure):
            run_async(self.moab_adapter.terminate_resource, resource_attributes=self.resource_attributes)

    def test_exception_handling(self):
        def test_exception_handling(to_raise, to_catch):
            with self.assertRaises(to_catch):
                with self.moab_adapter.handle_exceptions():
                    raise to_raise

        matrix = [(asyncio.TimeoutError(), TardisTimeout),
                  (asyncssh.Error(code=255,
                                  reason="Test",
                                  lang="Test"), TardisResourceStatusUpdateFailed),
                  (IndexError, TardisResourceStatusUpdateFailed),
                  (Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)

    def test_check_resource_id(self):
        with self.assertRaises(TardisError):
            self.moab_adapter.check_resource_id(AttributeDict(resource_id=1), regex=r"^(\d)$", response="2")
