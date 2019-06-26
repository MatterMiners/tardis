from tardis.adapters.sites.moab import MoabAdapter
from tardis.exceptions.executorexceptions import CommandExecutionFailure
from tardis.exceptions.tardisexceptions import TardisError
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.utilities.attributedict import AttributeDict
from tests.utilities.utilities import mock_executor_run_command
from tests.utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch

from datetime import datetime, timedelta

import asyncio
import asyncssh

__all__ = ['TestMoabAdapter']

TEST_RESOURCE_STATUS_RESPONSE = '''
<Data>
 <Object>queue</Object>
 <cluster LocalActiveNodes="68" LocalAllocProcs="1360" LocalConfigNodes="1037" LocalIdleNodes="7" LocalIdleProcs="7192" LocalUpNodes="922" LocalUpProcs="18432" RemoteActiveNodes="0" RemoteAllocProcs="0" RemoteConfigNodes="0" RemoteIdleNodes="0" RemoteIdleProcs="0" RemoteUpNodes="0" RemoteUpProcs="0" time="1553503935"/>
 <queue count="68" option="active">
  <job AWDuration="140875" Account="bw16g013" DRMJID="5096381.mg1.nemo.privat" EEDuration="44150" GJID="5096381" Group="ka_etp" JobID="5096381" JobName="startVM.py" MasterHost="n4545.nemo.privat" PAL="torque" ReqAWDuration="172800" ReqProcs="20" RsvStartTime="1553362801" RunPriority="-43322" StartPriority="-43322" StartTime="1553362801" StatPSDed="2813667.000000" StatPSUtl="140642.124800" State="Running" SubmissionTime="1553318572" SuspendDuration="0" User="ka_qb1555"/>
 </queue>
 <queue count="20" option="eligible">
  <job Account="bw16g013" EEDuration="72423" GJID="4761849" Group="ka_etp" JobID="4761849" JobName="startVM.py" ReqAWDuration="172800" ReqProcs="20" StartPriority="-38601" StartTime="0" State="Idle" SubmissionTime="1553431244" SuspendDuration="0" User="ka_qb1555"/>
 </queue>
 <queue count="0" option="blocked"/>
</Data><Data>
 <Object>queue</Object>
 <cluster LocalActiveNodes="0" LocalAllocProcs="0" LocalConfigNodes="1037" LocalIdleNodes="1" LocalIdleProcs="5895" LocalUpNodes="922" LocalUpProcs="18432" RemoteActiveNodes="0" RemoteAllocProcs="0" RemoteConfigNodes="0" RemoteIdleNodes="0" RemoteIdleProcs="0" RemoteUpNodes="0" RemoteUpProcs="0" time="1553521152"/>
 <queue count="1" option="completed" purgetime="86400">
  <job AWDuration="169164" Account="bw16g013" Class="compute" CompletionCode="0" CompletionTime="1553436477" DRMJID="5087810.mg1.nemo.privat" EEDuration="1457" GJID="5087810" Group="ka_etp" JobID="5087810" JobName="startVM.py" MasterHost="n4250.nemo.privat" PAL="torque" ReqAWDuration="172800" ReqNodes="1" ReqProcs="20" StartTime="1553267313" StatPSDed="3383282.000000" StatPSUtl="168401.142000" State="Completed" SubmissionTime="1553265273" SuspendDuration="0" User="ka_qb1555"/>
 </queue>
</Data>

'''

TEST_RESOURCE_STATUS_RESPONSE_RUNNING = '''
<Data>
 <Object>queue</Object>
 <cluster LocalActiveNodes="2" LocalAllocProcs="40" LocalConfigNodes="1038" LocalIdleNodes="5" LocalIdleProcs="555" LocalUpNodes="917" LocalUpProcs="18320" RemoteActiveNodes="0" RemoteAllocProcs="0" RemoteConfigNodes="0" RemoteIdleNodes="0" RemoteIdleProcs="0" RemoteUpNodes="0" RemoteUpProcs="0" time="1551959144"/>
 <queue count="2" option="active">
  <job AWDuration="80173" Account="bw16g013" DRMJID="4986904.mg1.nemo.privat" EEDuration="7575" GJID="4761849" Group="ka_etp" JobID="4761849" JobName="startVM.py" MasterHost="n3559.nemo.privat" PAL="torque" ReqAWDuration="172800" ReqProcs="20" RsvStartTime="1551878897" RunPriority="-43174" StartPriority="-43174" StartTime="1551878897" StatPSDed="1603250.600000" StatPSUtl="80162.530000" State="Running" SubmissionTime="1551871257" SuspendDuration="0" User="ka_qb1555"/>
  <job AWDuration="35418" Account="bw16g013" DRMJID="4989355.mg1.nemo.privat" EEDuration="1831" GJID="4761850" Group="ka_etp" JobID="4761850" JobName="startVM.py" MasterHost="n4131.nemo.privat" PAL="torque" ReqAWDuration="172800" ReqProcs="20" RsvStartTime="1551923652" RunPriority="-44134" StartPriority="-44134" StartTime="1551923652" StatPSDed="708148.200000" StatPSUtl="35407.410000" State="Running" SubmissionTime="1551921753" SuspendDuration="0" User="ka_qb1555"/>
 </queue>
 <queue count="0" option="eligible"/>
 <queue count="0" option="blocked"/>
</Data><Data>
 <Object>queue</Object>
 <cluster LocalActiveNodes="0" LocalAllocProcs="0" LocalConfigNodes="1037" LocalIdleNodes="1" LocalIdleProcs="5895" LocalUpNodes="922" LocalUpProcs="18432" RemoteActiveNodes="0" RemoteAllocProcs="0" RemoteConfigNodes="0" RemoteIdleNodes="0" RemoteIdleProcs="0" RemoteUpNodes="0" RemoteUpProcs="0" time="1553521152"/>
 <queue count="1" option="completed" purgetime="86400">
  <job AWDuration="169164" Account="bw16g013" Class="compute" CompletionCode="0" CompletionTime="1553436477" DRMJID="5087810.mg1.nemo.privat" EEDuration="1457" GJID="5087810" Group="ka_etp" JobID="5087810" JobName="startVM.py" MasterHost="n4250.nemo.privat" PAL="torque" ReqAWDuration="172800" ReqNodes="1" ReqProcs="20" StartTime="1553267313" StatPSDed="3383282.000000" StatPSUtl="168401.142000" State="Completed" SubmissionTime="1553265273" SuspendDuration="0" User="ka_qb1555"/>
 </queue>
</Data>

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
        self.test_site_config = config.TestSite
        self.test_site_config.MachineMetaData = self.machine_meta_data
        self.test_site_config.StartupCommand = 'startVM.py'
        self.test_site_config.StatusUpdate = 10
        self.test_site_config.MachineTypeConfiguration = self.machine_type_configuration
        self.test_site_config.executor = self.mock_executor.return_value

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
                             remote_resource_uuid=4761849,
                             resource_status=ResourceStatus.Booting,
                             created=datetime.strptime("Wed Jan 23 2019 15:01:47", '%a %b %d %Y %H:%M:%S'),
                             updated=datetime.strptime("Wed Jan 23 2019 15:02:17", '%a %b %d %Y %H:%M:%S'),
                             drone_uuid='testsite-4761849')

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

    def test_resource_status_raise(self):
        # Update interval is 10 minutes, so set last update back by 2 minutes in order to execute sacct command and
        # creation date to current date
        created_timestamp = datetime.now()
        new_timestamp = datetime.now() - timedelta(minutes=2)
        self.moab_adapter._moab_status._last_update = new_timestamp
        with self.assertRaises(TardisResourceStatusUpdateFailed):
            response = run_async(self.moab_adapter.resource_status,
                                 AttributeDict(resource_id=1351043, remote_resource_uuid=1351043,
                                               resource_state=ResourceStatus.Booting,
                                               created=created_timestamp))

    def test_resource_status_raise_past(self):
        # Update interval is 10 minutes, so set last update back by 11 minutes in order to execute sacct command and
        # creation date to 12 minutes ago
        creation_timestamp = datetime.now() - timedelta(minutes=12)
        last_update_timestamp = datetime.now() - timedelta(minutes=11)
        self.moab_adapter._moab_status._last_update = last_update_timestamp
        response = run_async(self.moab_adapter.resource_status, AttributeDict(resource_id=1390065,
                                                                              remote_resource_uuid=1351043,
                                                                              created=creation_timestamp))
        self.assertEqual(response.resource_status, ResourceStatus.Deleted)

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
                  (TardisResourceStatusUpdateFailed, TardisResourceStatusUpdateFailed),
                  (CommandExecutionFailure(message="Run test command",
                                           exit_code=1,
                                           stdout="Test",
                                           stderr="Test"), TardisResourceStatusUpdateFailed),
                  (Exception, TardisError)]

        for to_raise, to_catch in matrix:
            test_exception_handling(to_raise, to_catch)

    def test_check_remote_resource_uuid(self):
        with self.assertRaises(TardisError):
            self.moab_adapter.check_remote_resource_uuid(AttributeDict(remote_resource_uuid=1),
                                                         regex=r"^(\d)$", response="2")
