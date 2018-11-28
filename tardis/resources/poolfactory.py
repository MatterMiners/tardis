from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone

from cobald.composite.uniform import UniformComposite
from cobald.composite.factory import FactoryPool
from cobald.decorator.standardiser import Standardiser
from cobald.decorator.logger import Logger

from functools import partial
from importlib import import_module


def create_composite_pool(configuration='tardis.yml'):
    configuration = Configuration(configuration)

    composites = []

    batch_system = configuration.BatchSystem
    batch_system_adapter = getattr(import_module(name=f"tardis.adapter.{batch_system.adapter.lower()}"),
                                   f"{batch_system.adapter}Adapter")
    batch_system_agent = BatchSystemAgent(batch_system_adapter=batch_system_adapter())

    for site in configuration.Sites:
        site_adapter = getattr(import_module(name=f"tardis.adapter.{site.lower()}"), f'{site}Adapter')
        for machine_type in getattr(configuration, site).MachineTypes:
            drone_factory = partial(create_drone, site_agent=SiteAgent(site_adapter(machine_type=machine_type,
                                                                                    site_name=site.lower())),
                                    batch_system_agent=batch_system_agent)
            cpu_cores = getattr(configuration, site).MachineMetaData[machine_type]['Cores']
            composites.append(Logger(Standardiser(FactoryPool(factory=drone_factory),
                                                  minimum=cpu_cores,
                                                  granularity=cpu_cores),
                                     name=site.lower()))

    return UniformComposite(*composites)


def create_drone(site_agent, batch_system_agent):
    return Drone(site_agent=site_agent, batch_system_agent=batch_system_agent)
