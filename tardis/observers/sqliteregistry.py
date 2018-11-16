from ..interfaces.observer import Observer

import logging


class SqliteRegistry(Observer):
    def notify(self, state, resource_attributes):
        logging.debug(f"Drone: {str(resource_attributes)} has changed state to {state}")
