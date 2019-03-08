import yaml


def enable_yaml_load(tag):
    def yaml_load_decorator(cls):
        def class_factory(loader, node):
            if isinstance(node, yaml.nodes.MappingNode):
                parameters = loader.construct_mapping(node)
                new_cls = cls(**parameters)
            elif isinstance(node, yaml.nodes.ScalarNode):
                parameter = loader.construct_scalar(node)
                new_cls = cls(parameter)
            elif isinstance(node, yaml.nodes.SequenceNode):
                parameters = loader.construct_sequence(node)
                new_cls = cls(*parameters)
            return new_cls
        yaml.add_constructor(tag, class_factory)
        return cls
    return yaml_load_decorator