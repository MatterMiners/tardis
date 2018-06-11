from ..interfaces.borg import Borg
import yaml


class AttrDict(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError("{} is not a valid attribute".format(item))

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, item):
        try:
            del self[item]
        except KeyError:
            raise AttributeError("{} is not a valid attribute".format(item))


class Configuration(Borg):
    _shared_state = AttrDict()

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
            self._shared_state.update(self.convert_configuration(yaml.load(config_file)))

    def convert_configuration(self, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self.convert_configuration(value)
            return AttrDict(obj)
        elif isinstance(obj, list):
            return [self.convert_configuration(item) for item in obj]
        else:
            return obj
