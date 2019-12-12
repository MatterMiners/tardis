from ..utilities.attributedict import AttributeDict

from abc import ABCMeta, abstractmethod
from enum import Enum


class ResourceStatus(Enum):
    """
    Status of the resource at the resource provider (batch system, cloud provider, etc.)
    """

    Booting = 1
    Running = 2
    Stopped = 3
    Deleted = 4
    Error = 5


class SiteAdapter(metaclass=ABCMeta):
    """
    Abstract base class defining the interface for SiteAdapters which provide
    access to various Cloud APIs and batch systems in order to manage
    opportunistic resources.
    """

    @property
    def configuration(self) -> AttributeDict:
        """
        Property to provide access to configuration of the actual
        implementation of the SiteAdapter.
        :return: returns the configuration of the Site Adapter
        :rtype: AttributeDict
        """
        try:
            # noinspection PyUnresolvedReferences
            return self._configuration
        except AttributeError as ae:
            raise AttributeError(
                f"Class {self.__class__.__name__} must have an '_configuration' instance variable"  # noqa
            ) from ae

    @abstractmethod
    async def deploy_resource(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        """
        Abstract method to define the interface to deploy a new resource at a
        resource provider.
        :param resource_attributes: Contains describing attributes of the resource,
        defined in the :py:class:`~tardis.resources.drone.Drone` implementation!
        :type resource_attributes: AttributeDict
        :return: Contains updated describing attributes of the resource.
        :rtype: AttributeDict
        """
        raise NotImplementedError

    def drone_uuid(self, uuid: str) -> str:
        """
        Returns the drone uuid consisting of the lower case site name and the
        first 10 bytes of uuid4 due to constraints on length of a full DNS name
        (253 bytes).
        :param uuid: The first 10 bytes of a uuid4
        :type uuid: str
        :return: The drone uuid consisting of the lower case site name and the
        first 10 bytes of uuid4.
        :rtype: str
        """
        return f"{self.site_name.lower()}-{uuid}"

    @abstractmethod
    def handle_exceptions(self):
        """
        Abstract method defining the interface to handle exception occurring
        during interacting with the resource provider.
        :return: None
        """
        raise NotImplementedError

    @staticmethod
    def handle_response(
        response, key_translator: dict, translator_functions: dict, **additional_content
    ):
        """
        Method to handle the responses of the resource provider and translating
        it to a uniform format.
        :param response: A dictionary containing the response of the
        resource provider.
        :type response: dict
        :param key_translator: A dictionary containing the translation of keys
        of the original response of the provider in keys of the common format.
        :type key_translator: dict
        :param translator_functions: A dictionary containing functions to
        transform value of the original reponse of the provider into values of
        the common format.
        :type translator_functions: dict
        :param additional_content: Additional content to be put into response,
        which is not part of the original response of the resource provider.
        :return: Translated response of the resource provider in a common format.
        :rtype: dict
        """
        translated_response = AttributeDict()

        for translated_key, key in key_translator.items():
            try:
                translated_response[translated_key] = translator_functions.get(
                    key, lambda x: x
                )(response[key])
            except KeyError:
                continue

        for key, value in additional_content.items():
            translated_response[key] = value

        return translated_response

    @property
    def drone_minimum_lifetime(self) -> [int, None]:
        try:
            return self.configuration.drone_minimum_lifetime
        except AttributeError:
            return None

    @property
    def machine_meta_data(self) -> AttributeDict:
        """
        Property to access the machine_meta_data (like cores, memory and disk)
        of a resource.
        :return: The machine_meta_data of a resource.
        :rtype: AttributeDict
        """
        return self.configuration.MachineMetaData[self.machine_type]

    @property
    def machine_type(self) -> str:
        """
        Property to access the machine_type (flavour) of a resource and ensuring
        that all sub-classes of the SiteAdapter have a _machine_type
        class variable .
        :return: The machine_type of a resource.
        :rtype: str
        """
        try:
            # noinspection PyUnresolvedReferences
            return self._machine_type
        except AttributeError as ae:
            raise AttributeError(
                f"Class {self.__class__.__name__} must have an '_machine_type' instance variable"  # noqa
            ) from ae

    @property
    def machine_type_configuration(self) -> AttributeDict:
        """
        Property to access the machine_type_configuration (arguments of the API
        calls to the provider) of a resource.
        :return: The machine_type_configuration of a resource.
        :rtype: AttributeDict
        """
        return self.configuration.MachineTypeConfiguration[self.machine_type]

    @abstractmethod
    async def resource_status(
        self, resource_attributes: AttributeDict
    ) -> AttributeDict:
        """
        Abstract method to define the interface to check the status of resources
        at a resource provider.
        :param resource_attributes: Contains describing attributes of the resource,
        defined in the :py:class:`~tardis.resources.drone.Drone` implementation!
        :type resource_attributes: AttributeDict
        :return: Contains updated describing attributes of the resource.
        :rtype: AttributeDict
        """
        raise NotImplementedError

    @property
    def site_name(self) -> str:
        """
        Property to access the site_name of a resource and ensuring
        that all sub-classes of the SiteAdapter have a _site_name
        class variable.
        :return: The site_name of a resource.
        :rtype: str
        """
        try:
            # noinspection PyUnresolvedReferences
            return self._site_name
        except AttributeError as ae:
            raise AttributeError(
                f"Class {self.__class__.__name__} must have an '_site_name' instance variable"  # noqa
            ) from ae

    @abstractmethod
    async def stop_resource(self, resource_attributes: AttributeDict):
        """
        Abstract method to define the interface to stop resources at a resource
        provider.
        :param resource_attributes: Contains describing attributes of the resource,
        defined in the :py:class:`~tardis.resources.drone.Drone` implementation!
        :type resource_attributes: AttributeDict
        :return: Contains updated describing attributes of the resource.
        :rtype: AttributeDict
        """
        raise NotImplementedError

    @abstractmethod
    async def terminate_resource(self, resource_attributes: AttributeDict):
        """
        Abstract method to define the interface to terminate resources at a
        resource provider.
        :param resource_attributes: Contains describing attributes of the resource,
        defined in the :py:class:`~tardis.resources.drone.Drone` implementation!
        :type resource_attributes: AttributeDict
        :return: Contains updated describing attributes of the resource.
        :rtype: AttributeDict
        """
        raise NotImplementedError
