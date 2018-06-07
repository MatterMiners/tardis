from ..interfaces.borg import Borg
import asyncio


class Looper(Borg):
    def __init__(self):
        super(Looper, self).__init__()
        if not hasattr(self, '_event_loop'):
            self._event_loop = asyncio.get_event_loop()

    def get_event_loop(self):
        return None
