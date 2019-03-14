from ..interfaces.borg import Borg
from ..utilities.attributedict import AttributeDict
from ..utilities.attributedict import convert_to_attribute_dict
# Need to import all pyyaml loadable classes (bootstrapping problem) FIX ME
from ..utilities.executors import *  # noqa: F403, F401

from base64 import b64encode
import os
import yaml


def encode_user_data(obj):
    if isinstance(obj, AttributeDict):
        for key, value in obj.items():
            if key == 'user_data':
                with open(os.path.join(os.getcwd(), obj[key]), 'rb') as f:
                    obj[key] = b64encode(f.read())
            else:
                obj[key] = encode_user_data(value)
        return obj
    elif isinstance(obj, list):
        return [encode_user_data(item) for item in obj]
    else:
        return obj


class Configuration(Borg):
    _shared_state = AttributeDict()

    def __init__(self, config_file: str = None):
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
            self._shared_state.update(encode_user_data(convert_to_attribute_dict(yaml.safe_load(config_file))))
