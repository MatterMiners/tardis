from ..interfaces.borg import Borg
from ..utilities.attributedict import AttributeDict
from ..utilities.attributedict import convert_to_attribute_dict

# Need to import all pyyaml loadable classes (bootstrapping problem) FIX ME
from ..utilities.executors import *  # noqa: F403, F401
from ..utilities.simulators import *  # noqa: F403, F401

from cobald.daemon.config.mapping import Translator
from cobald.daemon.plugins import constraints as plugin_constraints

from base64 import b64encode
import os
import yaml


def translate_config(obj):
    if isinstance(obj, AttributeDict):
        translated_obj = AttributeDict(obj)
        for key, value in obj.items():
            if key == "user_data":  # base64 encode user data
                with open(os.path.join(os.getcwd(), obj[key]), "rb") as f:
                    translated_obj[key] = b64encode(f.read())
            elif key == "__type__":  # do legacy object initialisation
                return Translator().translate_hierarchy(obj)
            else:
                translated_obj[key] = translate_config(value)
        return translated_obj
    elif isinstance(obj, list):
        return [translate_config(item) for item in obj]
    else:
        return obj


@plugin_constraints(before={"pipeline"})
class Configuration(Borg):
    _shared_state = AttributeDict()

    def __init__(self, configuration: [str, dict] = None):
        super(Configuration, self).__init__()
        if configuration:
            if isinstance(configuration, str):  # interpret string as file name
                self.load_config(configuration)
            else:
                self.update_config(configuration)

    def load_config(self, config_file: str) -> None:
        """
        Loads YAML configuration file into shared state of the configuration borg
        :param config_file: The name of the configuration file to be loaded
        :type config_file: str
        """
        with open(config_file, "r") as config_file:
            self.update_config(yaml.safe_load(config_file))

    def update_config(self, configuration: dict):
        """
        Updates the shared state of the configuration borg
        :param configuration: Dictionary containing the configuration
        :type configuration: dict
        """
        self._shared_state.update(
            translate_config(convert_to_attribute_dict(configuration))
        )
