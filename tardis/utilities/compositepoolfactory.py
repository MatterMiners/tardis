from ..adapter.htcondor import HTCondorAdapter
from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone

from cobald.composite.uniform import UniformComposite

from importlib import import_module


def create_composite_pool():
    configuration = Configuration('tardis.yml')

    drones = []

    batch_system_agent = BatchSystemAgent(batch_system_adapter=HTCondorAdapter())

    for site in configuration.Sites:
        site_adapter = getattr(import_module(name="tardis.adapter.{}".format(site.lower())), '{}Adapter'.format(site))
        for machine_type in getattr(configuration, site).MachineTypes:
            drones.extend([(Drone(site_agent=SiteAgent(site_adapter(machine_type=machine_type,
                                                                    site_name=site.lower())),
                                  batch_system_agent=batch_system_agent)) for _ in range(1)])

    return UniformComposite(*drones)
