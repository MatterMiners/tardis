from ..utilities.attributedict import AttributeDict

from abc import ABCMeta, abstractmethod
from enum import Enum


class ResourceStatus(Enum):
    Booting = 1
    Running = 2
    Stopped = 3
    Deleted = 4
    Error = 5


class SiteAdapter(metaclass=ABCMeta):
    @abstractmethod
    async def deploy_resource(
            self, resource_attributes: AttributeDict) -> AttributeDict:
        return NotImplemented

    def drone_uuid(self, uuid) -> str:
        return f"{self.site_name.lower()}-{uuid}"

    def handle_exceptions(self):
        return NotImplemented

    @staticmethod
    def handle_response(response, key_translator: dict,
                        translator_functions: dict, **additional_content):
        translated_response = AttributeDict()

        for translated_key, key in key_translator.items():
            try:
                translated_response[translated_key] = translator_functions.get(
                    key, lambda x: x)(response[key])
            except KeyError:
                continue

        for key, value in additional_content.items():
            translated_response[key] = value

        return translated_response

    @property
    def machine_meta_data(self) -> AttributeDict:
        return NotImplemented

    @property
    def machine_type(self) -> str:
        return NotImplemented

    @abstractmethod
    async def resource_status(
            self, resource_attributes: AttributeDict) -> AttributeDict:
        return NotImplemented

    @property
    def site_name(self) -> str:
        return NotImplemented

    @abstractmethod
    async def stop_resource(self, resource_attributes: AttributeDict):
        return NotImplemented

    @abstractmethod
    async def terminate_resource(self, resource_attributes: AttributeDict):
        return NotImplemented
