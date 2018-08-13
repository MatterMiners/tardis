from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisTimeout
from ..interfaces.batchsystemadapter import MachineStatus
from ..interfaces.state import State
from ..interfaces.siteadapter import ResourceStatus

import asyncio
import logging


class RequestState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in RequestState".format(drone))
        try:
            drone.resource_attributes.update(await drone.site_agent.deploy_resource(unique_id=drone.unique_id))
        except (TardisAuthError, TardisTimeout):
            drone.state = DownState()  # static state transition
        else:
            drone.state = BootingState()  # static state transition
        finally:
            # Can be removed in production code
            await asyncio.sleep(0.5)


class BootingState(State):
    @classmethod
    async def run(cls, drone):
        logging.info("Drone {} in BootingState".format(drone))
        try:
            drone.resource_attributes.update(await drone.site_agent.resource_status(drone.resource_attributes))
            logging.info('Resource attributes: {}'.format(drone.resource_attributes))
        except (TardisAuthError, TardisTimeout):
            #  Retry to get current state of the resource
            drone.state = BootingState()  # static state transition
        else:
            drone.state = cls.transition[drone.resource_attributes.resource_status]()
        finally:
            # Can be removed in production code
            await asyncio.sleep(0.5)


class IntegrateState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in IntegrateState".format(drone))
        await drone.batch_system_agent.integrate_machine(dns_name=drone.resource_attributes['dns_name'])
        await asyncio.sleep(0.5)
        drone.state = IntegratingState()  # static state transition


class IntegratingState(State):
    @classmethod
    async def run(cls, drone):
        logging.info("Drone {} in IntegratingState".format(drone))
        machine_status = await drone.batch_system_agent.get_machine_status(dns_name=drone.resource_attributes[
            'dns_name'])
        await asyncio.sleep(0.5)
        drone.state = cls.transition[machine_status]()


class AvailableState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in AvailableState".format(drone))
        await asyncio.sleep(60)
        drone._allocation = await drone.batch_system_agent.get_allocation(dns_name=drone.resource_attributes[
            'dns_name'])
        drone._utilisation = await drone.batch_system_agent.get_utilization(dns_name=drone.resource_attributes[
            'dns_name'])
        drone._supply = drone.maximum_demand
        if not drone.demand:
            drone.state = DrainingState()  # static state transition
        else:
            drone.state = AvailableState()  # static state transition


class DrainState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DrainState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = DrainingState()  # static state transition


class DrainingState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DrainingState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = DisintegrateState()  # static state transition


class DisintegrateState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DisintegrateState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = ShutDownState()  # static state transition


class ShutDownState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in ShutDownState".format(drone))
        logging.info('Destroying VM with ID {}'.format(drone.resource_attributes.resource_id))
        await drone.site_agent.terminate_resource(drone.resource_attributes)
        await asyncio.sleep(0.5)
        drone.state = CleanupState()  # static state transition


class CleanupState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in CleanupState".format(drone))
        logging.info('Destroying VM with ID {}'.format(drone.resource_attributes.resource_id))
        await drone.site_agent.terminate_resource(drone.resource_attributes)
        await asyncio.sleep(0.5)
        drone.state = DownState()  # static state transition


class DownState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DownState".format(drone))


# define allowed state transitions
BootingState.transition = {ResourceStatus.Booting: BootingState,
                           ResourceStatus.Running: IntegrateState}

IntegratingState.transition = {MachineStatus.NotAvailable: IntegratingState,
                               MachineStatus.Available: AvailableState}
