from abc import abstractmethod
from collections import Mapping
from copy import copy, deepcopy


class BaseOperator(Mapping):
    """
    Base operator.
    """

    @property
    @abstractmethod
    def query(self) -> dict:
        ...

    def __getitem__(self, item):
        return self.query[item]

    def __iter__(self):
        return iter(self.query)

    def __len__(self):
        return len(self.query)

    def __repr__(self):
        return repr(self.query)

    def __str__(self):
        return str(self.query)

    def __copy__(self):
        return copy(self.query)

    def __deepcopy__(self, memodict={}):
        return deepcopy(self.query)

    def copy(self):
        return copy(self)
