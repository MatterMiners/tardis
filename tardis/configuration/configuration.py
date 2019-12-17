from ..interfaces.borg import Borg
from ..utilities.attributedict import AttributeDict
from ..utilities.attributedict import convert_to_attribute_dict

# Need to import all pyyaml loadable classes (bootstrapping problem) FIX ME
from ..utilities.executors import *  # noqa: F403, F401
from ..utilities.simulators import *  # noqa: F403, F401

from cobald.daemon.config.mapping import Translator

from base64 import b64encode
import os
import yaml


def translate_config(obj):
    if isinstance(obj, AttributeDict):
        for key, value in obj.items():
            if key == "user_data":  # base64 encode user data
                with open(os.path.join(os.getcwd(), obj[key]), "rb") as f:
                    obj[key] = b64encode(f.read())
            elif key == "__type__":  # do legacy object initialisation
                return Translator().translate_hierarchy(obj)
            else:
                obj[key] = translate_config(value)
        return obj
    elif isinstance(obj, list):
        return [translate_config(item) for item in obj]
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
        with open(config_file, "r") as config_file:
            self._shared_state.update(
                translate_config(convert_to_attribute_dict(yaml.safe_load(config_file)))
            )
