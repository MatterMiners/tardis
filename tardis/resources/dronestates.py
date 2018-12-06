from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisQuotaExceeded
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed
from ..interfaces.batchsystemadapter import MachineStatus
from ..interfaces.state import State
from ..interfaces.siteadapter import ResourceStatus

import asyncio
import logging


class RequestState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in RequestState")
        try:
            drone.resource_attributes.update(await drone.site_agent.deploy_resource(drone.resource_attributes))
        except (TardisAuthError, TardisTimeout, TardisQuotaExceeded):
            drone.state = DownState()  # static state transition
        except TardisResourceStatusUpdateFailed:
            await asyncio.sleep(1.0)
            drone.state = RequestState()
        else:
            drone.state = BootingState()  # static state transition
        finally:
            # Can be removed in production code
            await asyncio.sleep(0.5)


class BootingState(State):
    @classmethod
    async def run(cls, drone):
        logging.info(f"Drone {drone} in BootingState")
        try:
            drone.resource_attributes.update(await drone.site_agent.resource_status(drone.resource_attributes))
            logging.info(f'Resource attributes: {drone.resource_attributes}')
        except (TardisAuthError, TardisTimeout):
            #  Retry to get current state of the resource
            drone.state = BootingState()  # static state transition
        except TardisResourceStatusUpdateFailed:
            await asyncio.sleep(1.0)
            drone.state = BootingState()
        else:
            drone.state = cls.transition[drone.resource_attributes.resource_status]()
        finally:
            # Can be removed in production code
            await asyncio.sleep(0.5)


class IntegrateState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in IntegrateState")
        await drone.batch_system_agent.integrate_machine(dns_name=drone.resource_attributes['dns_name'])
        await asyncio.sleep(0.5)
        drone.state = IntegratingState()  # static state transition


class IntegratingState(State):
    @classmethod
    async def run(cls, drone):
        logging.info(f"Drone {drone} in IntegratingState")
        machine_status = await drone.batch_system_agent.get_machine_status(dns_name=drone.resource_attributes[
            'dns_name'])
        await asyncio.sleep(0.5)
        drone.state = cls.transition[machine_status]()


class AvailableState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in AvailableState")
        await asyncio.sleep(10)

        machine_status = await drone.batch_system_agent.get_machine_status(dns_name=drone.resource_attributes[
            'dns_name'])

        if not drone.demand:
            drone._supply = 0.0
            drone.state = DrainState()  # static state transition
            return

        if machine_status == MachineStatus.NotAvailable:
            drone._supply = 0.0
            drone.state = ShutDownState()  # static state transition
            return

        drone._allocation = await drone.batch_system_agent.get_allocation(dns_name=drone.resource_attributes[
            'dns_name'])
        drone._utilisation = await drone.batch_system_agent.get_utilization(dns_name=drone.resource_attributes[
            'dns_name'])
        drone._supply = drone.maximum_demand
        drone.state = AvailableState()  # static state transition


class DrainState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in DrainState")
        await drone.batch_system_agent.drain_machine(dns_name=drone.resource_attributes[
            'dns_name'])
        await asyncio.sleep(0.5)
        drone.state = DrainingState()  # static state transition


class DrainingState(State):
    @classmethod
    async def run(cls, drone):
        logging.info(f"Drone {drone} in DrainingState")
        await asyncio.sleep(0.5)
        machine_status = await drone.batch_system_agent.get_machine_status(dns_name=drone.resource_attributes[
            'dns_name'])
        drone.state = cls.transition[machine_status]()


class DisintegrateState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in DisintegrateState")
        await asyncio.sleep(0.5)
        drone.state = ShutDownState()  # static state transition


class ShutDownState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in ShutDownState")
        logging.info(f'Stopping VM with ID {drone.resource_attributes.resource_id}')
        try:
            await drone.site_agent.stop_resource(drone.resource_attributes)
        except TardisResourceStatusUpdateFailed:
            await asyncio.sleep(1.0)
            drone.state = ShutDownState()
        await asyncio.sleep(0.5)
        drone.state = ShuttingDownState()  # static state transition


class ShuttingDownState(State):
    @classmethod
    async def run(cls, drone):
        logging.info(f"Drone {drone} in ShuttingDownState")
        logging.info(f'Checking Status of VM with ID {drone.resource_attributes.resource_id}')
        try:
            drone.resource_attributes.update(await drone.site_agent.resource_status(drone.resource_attributes))
        except TardisResourceStatusUpdateFailed:
            await asyncio.sleep(1.0)
            drone.state = ShuttingDownState()
        drone.state = cls.transition[drone.resource_attributes.resource_status]()
        await asyncio.sleep(0.5)


class CleanupState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in CleanupState")
        logging.info(f'Destroying VM with ID {drone.resource_attributes.resource_id}')
        try:
            await drone.site_agent.terminate_resource(drone.resource_attributes)
        except TardisResourceStatusUpdateFailed:
            await asyncio.sleep(1.0)
            drone.state = CleanupState()
        await asyncio.sleep(0.5)
        drone.state = DownState()  # static state transition


class DownState(State):
    @staticmethod
    async def run(drone):
        logging.info(f"Drone {drone} in DownState")


# define allowed state transitions
BootingState.transition = {ResourceStatus.Booting: BootingState,
                           ResourceStatus.Running: IntegrateState}

IntegratingState.transition = {MachineStatus.NotAvailable: IntegratingState,
                               MachineStatus.Available: AvailableState}

DrainingState.transition = {MachineStatus.Draining: DrainingState,
                            MachineStatus.Available: DrainingState,
                            MachineStatus.Drained: DisintegrateState,
                            MachineStatus.NotAvailable: ShutDownState
                            }

ShuttingDownState.transition = {ResourceStatus.Running: ShuttingDownState,
                                ResourceStatus.Stopped: CleanupState}

