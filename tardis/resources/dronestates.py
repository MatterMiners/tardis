from ..interfaces.state import State

import asyncio
import logging


class RequestedState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in RequestedState".format(drone))
        response = await drone.site_agent.deploy_resource(unique_id=drone.unique_id)
        drone.vm_id = response['machine_id']
        drone.dns_name = response['dns_name']
        await asyncio.sleep(0.5)
        drone.state = BootingState()  # static state transition


class BootingState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in BootingState".format(drone))
        await drone.site_agent.resource_status(drone, name=drone.dns_name)
        await asyncio.sleep(0.5)
        drone.state = IntegratingState()  # static state transition


class IntegratingState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in IntegratingState".format(drone))
        await asyncio.sleep(60)
        drone.state = IdleState()  # static state transition


class IdleState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in IdleState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = BusyState()  # static state transition


class BusyState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in BusyState".format(drone))
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
        logging.info('Destroying VM with ID {}'.format(drone.vm_id))
        response = await drone.site_agent.terminate_resource(drone, id=drone.vm_id)
        await asyncio.sleep(0.5)
        drone.state = DownState()  # static state transition


class DownState(State):
    @staticmethod
    async def run(drone):
        logging.info("Drone {} in DownState".format(drone))
        await asyncio.sleep(10)
