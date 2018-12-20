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
    async def deploy_resource(self, resource_attributes):
        return NotImplemented

    def dns_name(self, unique_id):
        return f"{self.site_name.lower()}-{unique_id}"

    def handle_exceptions(self):
        return NotImplemented

    @staticmethod
    def handle_response(response, key_translator: dict, translator_functions: dict, **additional_content):
        translated_response = {}

        for translated_key, key in key_translator.items():
            try:
                translated_response[translated_key] = translator_functions.get(key,
                                                                               lambda x: x)(response[key])
            except KeyError:
                continue

        for key, value in additional_content.items():
            translated_response[key] = value

        return translated_response

    @property
    def machine_meta_data(self):
        return NotImplemented

    @property
    def machine_type(self):
        return NotImplemented

    @abstractmethod
    async def resource_status(self, resource_attributes):
        return NotImplemented

    @property
    def site_name(self):
        return NotImplemented

    @abstractmethod
    async def stop_resource(self, resource_attributes):
        return NotImplemented

    @abstractmethod
    async def terminate_resource(self, resource_attributes):
        return NotImplemented
