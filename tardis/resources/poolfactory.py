from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone
from ..resources.dronestates import RequestState

from cobald.composite.uniform import UniformComposite
from cobald.composite.factory import FactoryPool
from cobald.decorator.standardiser import Standardiser
from cobald.decorator.logger import Logger
from cobald.utility.primitives import infinity as inf

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

    plugins = load_plugins()

    for site in configuration.Sites:
        site_adapter = getattr(import_module(name=f"tardis.adapter.{site.adapter.lower()}"), f'{site.adapter}Adapter')
        for machine_type in getattr(configuration, site.name).MachineTypes:
            site_agent = SiteAgent(site_adapter(machine_type=machine_type, site_name=site.name))

            # Restore check_pointed resources from previously running tardis instance
            try:
                sql_registry = plugins['SqliteRegistry']
            except KeyError:
                check_pointed_drones = []
            else:
                check_pointed_resources = str_to_state(sql_registry.get_resources(site_name=site.name,
                                                                                  machine_type=machine_type))
                check_pointed_drones = [create_drone(site_agent=site_agent,
                                                     batch_system_agent=batch_system_agent,
                                                     plugins=plugins.values(),
                                                     **resource_attributes)
                                        for resource_attributes in check_pointed_resources]

            # create drone factory for COBalD FactoryPool
            drone_factory = partial(create_drone, site_agent=site_agent,
                                    batch_system_agent=batch_system_agent,
                                    plugins=plugins.values())
            cpu_cores = getattr(configuration, site.name).MachineMetaData[machine_type]['Cores']
            composites.append(Logger(Standardiser(FactoryPool(*check_pointed_drones,
                                                              factory=drone_factory),
                                                  minimum=cpu_cores,
                                                  maximum=site.quota if site.quota >= 0 else inf,
                                                  granularity=cpu_cores),
                                     name=f"{site.name.lower()}_{machine_type.lower()}"))

    return UniformComposite(*composites)


def create_drone(site_agent, batch_system_agent, plugins=None, resource_id=None, dns_name=None,
                 state=RequestState(), created=None, updated=None):
    return Drone(site_agent=site_agent, batch_system_agent=batch_system_agent, plugins=plugins,
                 resource_id=resource_id, dns_name=dns_name, state=state, created=created, updated=updated)


def load_plugins():
    try:
        plugin_configuration = Configuration().Plugins
    except AttributeError:
        return []
    else:
        def create_instance(plugin):
            return getattr(import_module(name=f"tardis.plugins.{plugin.lower()}"), f'{plugin}')()
        return {plugin: create_instance(plugin) for plugin in plugin_configuration.keys()}
