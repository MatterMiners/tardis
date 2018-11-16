from ..interfaces.observer import Observer

import asyncio
import logging


class SqliteRegistry(Observer):
    async def notify(self, state, resource_attributes):
        logging.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
        await asyncio.sleep(1)
