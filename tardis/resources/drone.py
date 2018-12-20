from .dronestates import RequestState
from .dronestates import DownState
from ..utilities.attributedict import AttributeDict
from cobald.daemon import service
from cobald.interfaces import Pool

from datetime import datetime

import asyncio
import logging
import uuid


@service(flavour=asyncio)
class Drone(Pool):
    def __init__(self, site_agent, batch_system_agent, plugins=None, resource_id=None, dns_name=None,
                 state=RequestState(), created=None, updated=None):
        self._site_agent = site_agent
        self._batch_system_agent = batch_system_agent
        self._plugins = plugins or []
        self._state = state

        self.resource_attributes = AttributeDict(site_name=self._site_agent.site_name,
                                                 machine_type=self.site_agent.machine_type,
                                                 resource_id=resource_id,
                                                 created=created or datetime.now(),
                                                 updated=updated or datetime.now(),
                                                 dns_name=dns_name or self.site_agent.dns_name(uuid.uuid4().hex[:10]))

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
                logging.debug(f"Garbage Collect Drone: {self.resource_attributes.dns_name}")
                return

    def register_plugins(self, observer):
        self._plugins.append(observer)

    def remove_plugins(self, observer):
        self._plugins.remove(observer)

    async def set_state(self, state):
        """Should be replaced by asynchronous state.setter property once available"""
        if state.__class__ != self.state.__class__:
            self.resource_attributes.updated = datetime.now()
        self._state = state
        await self.notify_plugins()

    @property
    def state(self):
        return self._state

    async def notify_plugins(self):
        for plugin in self._plugins:
            await plugin.notify(self.state, self.resource_attributes)
