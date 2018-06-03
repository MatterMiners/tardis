from abc import ABCMeta, abstractmethod

import asyncio
import logging


class BaseDroneState(metaclass=ABCMeta):
    transition = {}

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @staticmethod
    @abstractmethod
    async def run(drone):
        return NotImplemented


class InitialDroneState(BaseDroneState):
    @staticmethod
    async def run(drone):
        logging.info("Process {} in InitialDroneState".format(drone))
        await asyncio.sleep(0.5)
        drone.state = DoneDroneState()  # static state transition


class DoneDroneState(BaseDroneState):
    @staticmethod
    async def run(drone):
        logging.info("Process {} in DoneMachineState".format(drone))
