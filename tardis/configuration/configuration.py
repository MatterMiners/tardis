import yaml


class Configuration(object):
    _shared_state = {}

    def __init__(self, config_file: str=None):
        if not self._shared_state:
            self._shared_state = self.__dict__
        if config_file:
            self.load_config(config_file)
        self.__dict__ = self._shared_state

    def __getattr__(self, item):
        """
        Get attributes of Configuration by returning self.item
        :param item:
        :return: item
        """
        return getattr(self, item)

    def load_config(self, config_file: str) -> None:
        """
        Loads YAML configuration file into shared state of the configuration borg
        :param config_file: The name of the configuration file to be loaded
        :type config_file: str
        """
        with open(config_file, 'r') as config_file:
            self._shared_state.update(yaml.load(config_file))
