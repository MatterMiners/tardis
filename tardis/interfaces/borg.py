from abc import ABCMeta


class Borg(metaclass=ABCMeta):
    _shared_state = {}  # should be overwritten in all classes inheriting the borg

    def __init__(self):
        self.__dict__ = self._shared_state

    def __getattr__(self, item):
        """
        Get attributes of Configuration by returning self.item
        :param item:
        :return: item
        """
        if item not in self._shared_state:
            raise AttributeError(
                "Type object %r has no attribute %r)" % (self.__class__.__name__, item)
            )
        return getattr(self, item)
