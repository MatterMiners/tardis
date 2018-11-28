from .dronestates import RequestState
from .dronestates import DownState
from ..utilities.attributedict import AttributeDict
from cobald.interfaces import Pool
from cobald.daemon import service

import asyncio
import logging
import uuid


@service(flavour=asyncio)
class Drone(Pool):
    def __init__(self, site_agent, batch_system_agent, observers=None, unique_id=None, state=RequestState()):
        self._site_agent = site_agent
        self._batch_system_agent = batch_system_agent
        self._observers = observers or []
        self._state = state
        self.unique_id = unique_id or uuid.uuid4().hex[:10]

        self.resource_attributes = AttributeDict()

        self._allocation = 0.0
        self._demand = self.maximum_demand
        self._utilisation = 0.0
        self._supply = 0.0

    @property
    def allocation(self) -> float:
        return self._allocation

    @property
    def batch_system_agent(self):
        return self._batch_system_agent

    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        self._demand = value

    @property
    def maximum_demand(self) -> float:
        return self.site_agent.machine_meta_data['Cores']

    @property
    def supply(self) -> float:
        return self._supply

    @property
    def utilisation(self) -> float:
        return self._utilisation

    @property
    def site_agent(self):
        return self._site_agent

    async def run(self):
        while True:
            await self.state.run(self)
            await asyncio.sleep(1)
            if isinstance(self.state, DownState):
                logging.debug(f"Garbage Collect Drone: {self.unique_id}")
                return

    def register_observers(self, agent):
        self._observers.append(agent)

    def remove_observers(self, agent):
        self._observers.remove(agent)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        self.notify_observers()

    def notify_observers(self):
        for observer in self._observers:
            yield from observer.notify(self.resource_attributes)
