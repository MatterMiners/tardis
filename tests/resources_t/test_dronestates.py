from tardis.exceptions.tardisexceptions import TardisAuthError
from tardis.exceptions.tardisexceptions import TardisDroneCrashed
from tardis.exceptions.tardisexceptions import TardisTimeout
from tardis.exceptions.tardisexceptions import TardisQuotaExceeded
from tardis.exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from tardis.interfaces.batchsystemadapter import MachineStatus
from tardis.interfaces.siteadapter import ResourceStatus
from tardis.resources.dronestates import RequestState
from tardis.resources.dronestates import BootingState
from tardis.resources.dronestates import IntegrateState
from tardis.resources.dronestates import IntegratingState
from tardis.resources.dronestates import AvailableState
from tardis.resources.dronestates import DrainState
from tardis.resources.dronestates import DrainingState
from tardis.resources.dronestates import DisintegrateState
from tardis.resources.dronestates import ShutDownState
from tardis.resources.dronestates import ShuttingDownState
from tardis.resources.dronestates import CleanupState
from tardis.resources.dronestates import DownState
from tardis.utilities.attributedict import AttributeDict
from ..utilities.utilities import async_return
from ..utilities.utilities import run_async

from functools import partial
from unittest import TestCase
from unittest.mock import patch

import asyncio


class TestDroneStates(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_drone_patcher = patch('tardis.resources.drone.Drone')
        cls.mock_drone = cls.mock_drone_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_drone_patcher.stop()

    def setUp(self):
        async def mock_set_state(drone, state):
            drone.state = state
            f = asyncio.Future()
            f.set_result(None)
            return f

        self.drone = self.mock_drone.return_value
        self.drone.resource_attributes = AttributeDict(dns_name='test-923ABF', resource_id='0815')
        self.drone.demand = 8.0
        self.drone._supply = 8.0
        self.drone.set_state.side_effect = partial(mock_set_state, self.drone)
        self.drone.site_agent.deploy_resource.return_value = async_return(return_value=AttributeDict())
        self.drone.site_agent.resource_status.return_value = async_return(return_value=AttributeDict())
        self.drone.site_agent.stop_resource.return_value = async_return(return_value=AttributeDict())
        self.drone.site_agent.terminate_resource.return_value = async_return(return_value=AttributeDict())
        self.drone.batch_system_agent.integrate_machine.return_value = async_return(return_value=None)
        self.drone.batch_system_agent.disintegrate_machine.return_value = async_return(return_value=None)
        self.drone.batch_system_agent.drain_machine.return_value = async_return(return_value=None)
        self.drone.batch_system_agent.get_machine_status.return_value = async_return(return_value=None)
        self.drone.batch_system_agent.get_allocation.return_value = async_return(return_value=None)
        self.drone.batch_system_agent.get_utilization.return_value = async_return(return_value=None)

    def run_the_matrix(self, matrix, initial_state):
        for resource_status, machine_status, new_state in matrix:
            self.drone.site_agent.resource_status.return_value = async_return(
                return_value=AttributeDict(resource_status=resource_status))
            self.drone.batch_system_agent.get_machine_status.return_value = async_return(
                return_value=machine_status)
            self.drone.state.return_value = initial_state
            run_async(self.drone.state.return_value.run, self.drone)
            self.assertIsInstance(self.drone.state, new_state)

    def run_side_effects(self, initial_state, api_call_to_test, exceptions, finial_state):
        for exception in exceptions:
            self.drone.state.return_value = initial_state
            api_call_to_test.side_effect = exception()
            run_async(self.drone.state.return_value.run, self.drone)
            self.assertIsInstance(self.drone.state, finial_state)

        api_call_to_test.side_effect = None

    def test_request_state(self):
        self.drone.state.return_value = RequestState()
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, BootingState)

        self.run_side_effects(RequestState(), self.drone.site_agent.deploy_resource,
                              (TardisAuthError, TardisTimeout, TardisQuotaExceeded, TardisResourceStatusUpdateFailed),
                              DownState)

        self.run_side_effects(RequestState(), self.drone.site_agent.deploy_resource,
                              (TardisDroneCrashed,),
                              CleanupState)

    def test_booting_state(self):
        matrix = [(ResourceStatus.Booting, None, BootingState),
                  (ResourceStatus.Running, None, IntegrateState),
                  (ResourceStatus.Deleted, None, DownState),
                  (ResourceStatus.Stopped, None, CleanupState)]

        self.run_the_matrix(matrix, initial_state=BootingState)

        self.run_side_effects(BootingState(), self.drone.site_agent.resource_status,
                              (TardisAuthError, TardisTimeout, TardisResourceStatusUpdateFailed), BootingState)

        self.run_side_effects(BootingState(), self.drone.site_agent.resource_status,
                              (TardisDroneCrashed,), CleanupState)

    def test_integrate_state(self):
        self.drone.state.return_value = IntegrateState
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, IntegratingState)
        self.drone.batch_system_agent.integrate_machine.assert_called_with(dns_name='test-923ABF')

    def test_integrating_state(self):

        matrix = [(ResourceStatus.Running, MachineStatus.NotAvailable, IntegratingState),
                  (ResourceStatus.Running, MachineStatus.Available, AvailableState),
                  (ResourceStatus.Running, MachineStatus.Draining, DrainingState),
                  (ResourceStatus.Running, MachineStatus.Drained, DisintegrateState),
                  (ResourceStatus.Booting, MachineStatus.NotAvailable, BootingState),
                  (ResourceStatus.Booting, MachineStatus.Available, BootingState),
                  (ResourceStatus.Booting, MachineStatus.Drained, BootingState),
                  (ResourceStatus.Booting, MachineStatus.Draining, BootingState),
                  (ResourceStatus.Deleted, MachineStatus.NotAvailable, DownState),
                  (ResourceStatus.Stopped, MachineStatus.NotAvailable, CleanupState)]

        self.run_the_matrix(matrix, initial_state=IntegratingState)

    def test_available_state(self):
        matrix = [(ResourceStatus.Running, MachineStatus.Available, AvailableState),
                  (ResourceStatus.Running, MachineStatus.NotAvailable, IntegratingState),
                  (ResourceStatus.Running, MachineStatus.Draining, DrainingState),
                  (ResourceStatus.Running, MachineStatus.Drained, DisintegrateState),
                  (ResourceStatus.Booting, MachineStatus.NotAvailable, BootingState),
                  (ResourceStatus.Deleted, MachineStatus.NotAvailable, DownState),
                  (ResourceStatus.Stopped, MachineStatus.NotAvailable, CleanupState)]

        self.run_the_matrix(matrix, initial_state=AvailableState)

        # Test draining procedure if cobald sets drone demand to zero
        self.drone.demand = 0.0
        self.drone.state.return_value = AvailableState()
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, DrainState)
        self.assertEqual(self.drone._supply, 0.0)

    def test_drain_state(self):
        self.drone.state.return_value = DrainState
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, DrainingState)
        self.drone.batch_system_agent.drain_machine.assert_called_with(dns_name='test-923ABF')

    def test_draining_state(self):
        matrix = [(ResourceStatus.Running, MachineStatus.Draining, DrainingState),
                  (ResourceStatus.Running, MachineStatus.Available, DrainingState),
                  (ResourceStatus.Running, MachineStatus.Drained, DisintegrateState),
                  (ResourceStatus.Running, MachineStatus.NotAvailable, ShutDownState),
                  (ResourceStatus.Deleted, MachineStatus.NotAvailable, DownState),
                  (ResourceStatus.Stopped, MachineStatus.NotAvailable, CleanupState)]

        self.run_the_matrix(matrix, initial_state=DrainingState)

    def test_disintegrate_state(self):
        self.drone.state.return_value = DisintegrateState
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, ShutDownState)
        self.drone.batch_system_agent.disintegrate_machine.assert_called_with(dns_name='test-923ABF')

    def test_shutdown_state(self):
        matrix = [(ResourceStatus.Running, None, ShuttingDownState),
                  (ResourceStatus.Stopped, None, CleanupState),
                  (ResourceStatus.Deleted, None, DownState)]

        self.run_the_matrix(matrix, initial_state=ShutDownState)

        self.run_side_effects(ShutDownState, self.drone.site_agent.resource_status,
                              (TardisAuthError, TardisTimeout, TardisResourceStatusUpdateFailed), ShutDownState)

        self.run_side_effects(ShutDownState, self.drone.site_agent.resource_status,
                              (TardisDroneCrashed,), CleanupState)

    def test_shutting_down_state(self):
        matrix = [(ResourceStatus.Running, None, ShuttingDownState),
                  (ResourceStatus.Stopped, None, CleanupState),
                  (ResourceStatus.Deleted, None, DownState)]

        self.run_the_matrix(matrix, initial_state=ShuttingDownState)

    def test_cleanup_state(self):
        self.drone.state.return_value = CleanupState()
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertIsInstance(self.drone.state, DownState)
        self.drone.site_agent.terminate_resource.assert_called_with(self.drone.resource_attributes)

        self.run_side_effects(CleanupState(), self.drone.site_agent.terminate_resource,
                              (TardisDroneCrashed,), DownState)

        self.run_side_effects(CleanupState(), self.drone.site_agent.terminate_resource,
                              (TardisResourceStatusUpdateFailed,), CleanupState)

        self.drone.site_agent.terminate_resource.side_effect = None

    def test_down_state(self):
        self.drone.state.return_value = DownState()
        run_async(self.drone.state.return_value.run, self.drone)
        self.assertEqual(self.drone.demand, 0.0)
