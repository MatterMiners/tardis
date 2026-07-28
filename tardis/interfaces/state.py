from ..exceptions.tardisexceptions import TardisAuthError
from ..exceptions.tardisexceptions import TardisDroneCrashed
from ..exceptions.tardisexceptions import TardisTimeout
from ..exceptions.tardisexceptions import TardisResourceStatusUpdateFailed

from typing import Callable, Dict, Iterable, List, TYPE_CHECKING, Type

import asyncio
import logging

if TYPE_CHECKING:
    from tardis.resources.drone import Drone

logger = logging.getLogger("cobald.runtime.tardis.interfaces.state")


class State:
    task_pipeline: list[Callable[..., Any]] = []

    # to get a list of all available states and to avoid circular imports
    _state_registry: "dict[str, type[State]]" = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Every time a subclass is created, it adds itself here
        State._state_registry[cls.__name__] = cls

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__class__.__name__

    @classmethod
    def get_all_states(cls) -> Iterable[str]:
        return cls._state_registry.keys()

    @classmethod
    async def run(cls, drone: "Drone"):
        logger.info(f"Drone {drone.resource_attributes} in {cls.__name__}")
        try:
            target_state = await cls.transition_logic(
                *await asyncio.gather(*map(task, cls.task_pipeline))
            )
            next_state = await cls.on_leave(drone, target_state)
            await drone.set_state(next_state())
        except (
            TardisAuthError,
            TardisTimeout,
            TardisResourceStatusUpdateFailed,
        ):
            await drone.set_state(cls())
        except TardisDroneCrashed:
            # Clean up crashed resources
            # avoid circular import by using the state registry
            cleanup_cls = cls._state_registry.get("CleanupState")
            assert cleanup_cls is not None, "CleanupState is not implemented"
            downstate_cls = cls._state_registry["DownState"]
            assert downstate_cls is not None, "DownState is not implemented"
            if cls.__name__ == "CleanupState":
                # Avoid infinite recursion if CleanupState is the current state
                await drone.set_state(downstate_cls())
            else:
                await drone.set_state(cleanup_cls())

    @classmethod
    async def transition_logic(cls, *pipeline_results) -> "type[State]":
        """
        Override this to define which state to transition to.
        """
        return cls  # Default: stay in current state

    @classmethod
    async def on_leave(
        cls, drone: "Drone", target_state: "type[State]"
    ) -> "type[State]":
        """
        Called when leaving this state for target_state. Override to perform
        side effects. Defaults to target_state
        """
        return target_state
