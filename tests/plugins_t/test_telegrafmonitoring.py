from tardis.plugins.telegrafmonitoring import TelegrafMonitoring
from tardis.resources.dronestates import RequestState
from tardis.utilities.attributedict import AttributeDict


from unittest import TestCase

from ..utilities.utilities import run_async


class TestTelegrafMonitoring(TestCase):
    def setUp(self):
        self.plugin = TelegrafMonitoring()

    def test_notify(self):
        run_async(self.plugin.notify, RequestState(), AttributeDict())
