from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone
from ..observers.sqliteregistry import SqliteRegistry

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

    drone_registry = SqliteRegistry()
    drone_observers = (drone_registry,)

    for site in configuration.Sites:
        drone_registry.add_site(site.name)
        site_adapter = getattr(import_module(name=f"tardis.adapter.{site.adapter.lower()}"), f'{site.adapter}Adapter')
        for machine_type in getattr(configuration, site.name).MachineTypes:
            drone_registry.add_machine_types(site.name, machine_type)
            drone_factory = partial(create_drone, site_agent=SiteAgent(site_adapter(machine_type=machine_type,
                                                                                    site_name=site.name.lower())),
                                    batch_system_agent=batch_system_agent,
                                    drone_observers=drone_observers)
            cpu_cores = getattr(configuration, site.name.upper()).MachineMetaData[machine_type]['Cores']
            composites.append(Logger(Standardiser(FactoryPool(factory=drone_factory),
                                                  minimum=cpu_cores,
                                                  granularity=cpu_cores),
                                     name=f"{site.name.lower()}_{machine_type.lower()}"))

    return UniformComposite(*composites)


def create_drone(site_agent, batch_system_agent, drone_observers=None):
    if not drone_observers:
        drone_observers = []
    drone = Drone(site_agent=site_agent, batch_system_agent=batch_system_agent)
    for drone_observer in drone_observers:
        drone.register_observers(drone_observer)
    return drone
