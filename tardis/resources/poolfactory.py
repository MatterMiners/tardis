from typing import Iterable, Optional

from tardis.interfaces.plugin import Plugin
from tardis.interfaces.state import State
from ..agents.batchsystemagent import BatchSystemAgent
from ..agents.siteagent import SiteAgent
from ..configuration.configuration import Configuration
from ..resources.drone import Drone
from ..utilities.utils import load_states

from cobald.composite.weighted import WeightedComposite
from cobald.composite.factory import FactoryPool
from cobald.decorator.standardiser import Standardiser
from cobald.decorator.logger import Logger
from cobald.utility.primitives import infinity as inf

from functools import partial
from importlib import import_module


def create_composite_pool(configuration: str = None) -> WeightedComposite:
    configuration = Configuration(configuration)

    composites = []

    batch_system = configuration.BatchSystem
    batch_system_adapter = getattr(
        import_module(
            name=f"tardis.adapters.batchsystems.{batch_system.adapter.lower()}"
        ),
        f"{batch_system.adapter}Adapter",
    )
    batch_system_agent = BatchSystemAgent(batch_system_adapter=batch_system_adapter())

    plugins = load_plugins()

    for site in configuration.Sites:
        site_composites = []
        site_adapter = getattr(
            import_module(name=f"tardis.adapters.sites.{site.adapter.lower()}"),
            f"{site.adapter}Adapter",
        )
        for machine_type in getattr(configuration, site.name).MachineTypes:
            site_agent = SiteAgent(
                site_adapter(machine_type=machine_type, site_name=site.name)
            )

            check_pointed_resources = get_drones_to_restore(plugins, site, machine_type)
            check_pointed_drones = [
                create_drone(
                    site_agent=site_agent,
                    batch_system_agent=batch_system_agent,
                    plugins=plugins.values(),
                    **resource_attributes,
                )
                for resource_attributes in check_pointed_resources
            ]

            # create drone factory for COBalD FactoryPool
            drone_factory = partial(
                create_drone,
                site_agent=site_agent,
                batch_system_agent=batch_system_agent,
                plugins=plugins.values(),
            )

            site_composites.append(
                Logger(
                    FactoryPool(*check_pointed_drones, factory=drone_factory),
                    name=f"{site.name.lower()}_{machine_type.lower()}",
                )
            )
        composites.append(
            Standardiser(
                WeightedComposite(*site_composites, weight="utilisation"),
                maximum=site.quota if site.quota >= 0 else inf,
            )
        )

    return WeightedComposite(*composites, weight="utilisation")


def create_drone(
    site_agent: SiteAgent,
    batch_system_agent: BatchSystemAgent,
    plugins: Optional[Iterable[Plugin]] = None,
    remote_resource_uuid=None,
    drone_uuid=None,
    state: Optional[State] = None,
    created: float = None,
    updated: float = None,
):
    return Drone(
        site_agent=site_agent,
        batch_system_agent=batch_system_agent,
        plugins=plugins,
        remote_resource_uuid=remote_resource_uuid,
        drone_uuid=drone_uuid,
        state=state,
        created=created,
        updated=updated,
    )


def get_drones_to_restore(plugins: dict, site, machine_type: str):
    """Restore check_pointed resources from previously running tardis instance"""
    try:
        sql_registry = plugins["SqliteRegistry"]
    except KeyError:
        return []
    else:
        return load_states(
            sql_registry.get_resources(site_name=site.name, machine_type=machine_type)
        )


def load_plugins():
    """Load plugins specified in configuration"""
    try:
        plugin_configuration = Configuration().Plugins
    except AttributeError:
        return {}
    else:

        def create_instance(plugin):
            return getattr(
                import_module(name=f"tardis.plugins.{plugin.lower()}"), f"{plugin}"
            )()

        return {
            plugin: create_instance(plugin) for plugin in plugin_configuration.keys()
        }
