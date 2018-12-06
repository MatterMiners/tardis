from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone
from ..resources.dronestates import RequestState
from ..observers.sqliteregistry import SqliteRegistry

from cobald.composite.uniform import UniformComposite
from cobald.composite.factory import FactoryPool
from cobald.decorator.standardiser import Standardiser
from cobald.decorator.logger import Logger

from functools import partial
from importlib import import_module


def str_to_state(resources):
    for entry in resources:
        state_class = getattr(import_module(name=f"tardis.resources.dronestates"), f"{entry['state']}")
        entry['state'] = state_class()
    return resources


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
        site_adapter = getattr(import_module(name=f"tardis.adapter.{site.adapter.lower()}"), f'{site.adapter}Adapter')
        for machine_type in getattr(configuration, site.name).MachineTypes:
            site_agent = SiteAgent(site_adapter(machine_type=machine_type, site_name=site.name.lower()))

            # Restore check_pointed resources from previously running tardis instance
            check_pointed_resources = str_to_state(drone_registry.get_resources(site_name=site.name,
                                                                                machine_type=machine_type))
            check_pointed_drones = [create_drone(site_agent=site_agent,
                                                 batch_system_agent=batch_system_agent,
                                                 drone_observers=drone_observers,
                                                 **resource_attributes)
                                    for resource_attributes in check_pointed_resources]

            # create drone factory for COBalD FactoryPool
            drone_factory = partial(create_drone, site_agent=site_agent,
                                    batch_system_agent=batch_system_agent,
                                    drone_observers=drone_observers)
            cpu_cores = getattr(configuration, site.name).MachineMetaData[machine_type]['Cores']
            composites.append(Logger(Standardiser(FactoryPool(*check_pointed_drones,
                                                              factory=drone_factory),
                                                  minimum=cpu_cores,
                                                  granularity=cpu_cores),
                                     name=f"{site.name.lower()}_{machine_type.lower()}"))

    return UniformComposite(*composites)


def create_drone(site_agent, batch_system_agent, drone_observers=None, resource_id=None, dns_name=None,
                 state=RequestState(), created=None, updated=None):
    return Drone(site_agent=site_agent, batch_system_agent=batch_system_agent, observers=drone_observers,
                 resource_id=resource_id, dns_name=dns_name, state=state, created=created, updated=updated)
