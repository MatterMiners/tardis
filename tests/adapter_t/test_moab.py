from tardis.adapter.sites.moab import MoabAdapter
from tardis.utilities.attributedict import AttributeDict
from tardis.interfaces.siteadapter import ResourceStatus
from ..utilities.utilities import run_async

from unittest import TestCase
from unittest.mock import patch

try:
    from contextlib import asynccontextmanager
except ImportError:
    from aiotools import async_ctx_manager as asynccontextmanager

from datetime import datetime, timedelta

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

TEST_DEPLOY_RESOURCE_RESPONSE = '''

4761849
'''

TEST_TERMINATE_RESOURCE_RESPONSE = '''

job '4761849' cancelled

'''


class TestMoabAdapter(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_config_patcher = patch('tardis.adapter.sites.moab.Configuration')
        cls.mock_config = cls.mock_config_patcher.start()
        cls.mock_asyncssh_patcher = patch('tardis.adapter.sites.moab.asyncssh.connect')
        cls.mock_asyncssh = cls.mock_asyncssh_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_config_patcher.stop()
        cls.mock_asyncssh_patcher.stop()

    def mock_asyncssh_run(response):
        def decorator(func):
            def wrapper(self):
                @asynccontextmanager
                async def connect(*args, **kwargs):
                    class connection:
                        async def run(self, *args, **kwargs):
                            return self

                        @property
                        def stdout(self):
                            return response
                    yield connection()
                self.mock_asyncssh.side_effect = connect
                func(self)
                self.mock_asyncssh.side_effect = None
            return wrapper
        return decorator

    def setUp(self):
        config = self.mock_config.return_value
        test_site_config = config.TestSite
        test_site_config.remote_host = 'https://test.nova.client.local'
        test_site_config.login = 'TestUser'
        test_site_config.key = '/some/path/id_rsa'
        test_site_config.MachineMetaData = self.machine_meta_data

        self.moab_adapter = MoabAdapter(machine_type='test2large', site_name='TestSite')

    def tearDown(self):
        pass

    @property
    def machine_meta_data(self):
        return AttributeDict(test2large=AttributeDict(Cores=128, Walltime='02:00:00:00', Memory='120gb',
                                                      NodeType='1:ppn=20', StartupCommand='startVM.py'))

    @property
    def resource_attributes(self):
        return AttributeDict(machine_type='test2large',
                             site_name='TestSite',
                             resource_id=4761849,
                             resource_status=ResourceStatus.Booting,
                             created=datetime.strptime("Wed Jan 23 2019 15:01:47", '%a %b %d %Y %H:%M:%S'),
                             updated=datetime.strptime("Wed Jan 23 2019 15:02:17", '%a %b %d %Y %H:%M:%S'),
                             dns_name='testsite-4761849')

    @mock_asyncssh_run(TEST_DEPLOY_RESOURCE_RESPONSE)
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
        self.mock_asyncssh.assert_called_with('https://test.nova.client.local', username='TestUser',
                                              client_keys=['/some/path/id_rsa'])

    def test_machine_meta_data(self):
        self.assertEqual(self.moab_adapter.machine_meta_data, self.machine_meta_data['test2large'])

    def test_machine_type(self):
        self.assertEqual(self.moab_adapter.machine_type, 'test2large')

    def test_site_name(self):
        self.assertEqual(self.moab_adapter.site_name, 'TestSite')

    @mock_asyncssh_run(TEST_RESOURCE_STATUS_RESPONSE)
    def test_resource_status(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now())
        return_resource_attributes = run_async(self.moab_adapter.resource_status,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_asyncssh_run(TEST_TERMINATE_RESOURCE_RESPONSE)
    def test_stop_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.moab_adapter.stop_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)

    @mock_asyncssh_run(TEST_TERMINATE_RESOURCE_RESPONSE)
    def test_terminate_resource(self):
        expected_resource_attributes = self.resource_attributes
        expected_resource_attributes.update(updated=datetime.now(), resource_status=ResourceStatus.Stopped)
        return_resource_attributes = run_async(self.moab_adapter.terminate_resource,
                                               resource_attributes=self.resource_attributes)
        if return_resource_attributes.updated - expected_resource_attributes.updated > timedelta(seconds=1):
            raise Exception("Update time wrong!")
        del expected_resource_attributes.updated, return_resource_attributes.updated
        self.assertEqual(return_resource_attributes, expected_resource_attributes)
