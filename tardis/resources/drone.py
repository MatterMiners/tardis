from .dronestates import InitialDroneState
from cobald.interfaces.actor import Actor
from cobald.interfaces.pool import Pool

import asyncio
import uuid


class Drone(Actor, Pool):
    def __init__(self, agents, id=None, state=InitialDroneState()):
        self._agents = agents
        self._state = state
        self.id = id or uuid.uuid4()
        self._allocation = 0.0
        self._consumption = 0.0
        self._demand = 0.0
        self._supply = 0.0
        self._utilisation = 0.0

    @property
    def allocation(self) -> float:
        return self._allocation

    @property
    def consumption(self) -> float:
        return self._consumption

    @property
    def demand(self):
        return self._demand

    @demand.setter
    def demand(self, value):
        self._demand = value

    @property
    def supply(self):
        return self._supply

    @property
    def utilisation(self) -> float:
        return self._utilisation

    async def run(self):
        while True:
            await self.state.run(self)
            await asyncio.sleep(1)

    def register_agents(self, agent):
        self._agents.append(agent)

    def remove_agents(self, agent):
        self._agents.remove(agent)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        self.update_agents()

    def update_agents(self):
        for agent in self._agents:
            agent.update(self)
