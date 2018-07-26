from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisTimeout
from ..interfaces.batchsystemadapter import MachineActivities
from ..interfaces.state import State

import asyncio
import logging


class RequestedState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in RequestedState".format(drone))
        try:
            drone.resource_attributes = await drone.site_agent.deploy_resource(unique_id=drone.unique_id)
        except (TardisAuthError, TardisTimeout):
            # Retry provisioning of the resource
            drone.state = RequestedState()  # static state transition
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
        except (TardisAuthError, TardisTimeout):
            #  Retry to get current state of the resource
            drone.state = BootingState()  # static state transition
        else:
            drone.state = IntegratingState()  # static state transition
            # drone.state = cls.transition(drone.resource_attributes.resource_status)
        finally:
            # Can be removed in production code
            await asyncio.sleep(0.5)


class IntegratingState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in IntegratingState".format(drone))
        await drone.batch_system_agent.integrate_machine(dns_name=drone.resource_attributes['dns_name'])
        await asyncio.sleep(60)
        drone.state = AvailableState()  # static state transition


class AvailableState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in IdleState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = DrainingState()  # static state transition


class DrainingState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DrainingState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = ShutDownState()  # static state transition


class ShutDownState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in ShutDownState".format(drone))
        logging.info('Destroying VM with ID {}'.format(drone.resource_attributes.resource_id))
        await drone.site_agent.terminate_resource(drone.resource_attributes)
        await asyncio.sleep(0.5)
        drone.state = DownState()  # static state transition


class DownState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DownState".format(drone))
        await asyncio.sleep(60)
        drone.state = RequestedState()  # static state transition


# define allowed state transitions
RequestedState.transition = {'REQUESTED': RequestedState,
                             'BOOTING': BootingState,
                             'DOWN': DownState}

BootingState.transition = {'BOOTING': BootingState,
                           'INTEGRATING': IntegratingState,
                           'DOWN': DownState}
