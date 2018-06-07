from ..interfaces.borg import Borg
import yaml


class Configuration(Borg):
    def __init__(self, config_file: str=None):
        super(Configuration, self).__init__()
        if config_file:
            self.load_config(config_file)

    def load_config(self, config_file: str) -> None:
        """
        Loads YAML configuration file into shared state of the configuration borg
        :param config_file: The name of the configuration file to be loaded
        :type config_file: str
        """
        with open(config_file, 'r') as config_file:
            self._shared_state.update(yaml.load(config_file))
