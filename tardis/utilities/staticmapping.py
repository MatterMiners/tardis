from collections.abc import Mapping


class StaticMapping(Mapping):
    def __init__(self, **kwargs):
        self._data = dict(**kwargs)

    def __getitem__(self, item):
        return self._data[item]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)
