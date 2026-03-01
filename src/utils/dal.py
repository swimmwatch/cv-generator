import abc


class BaseAsyncDAL(abc.ABC):
    @abc.abstractmethod
    async def all(self):
        pass

    @abc.abstractmethod
    async def first(self):
        pass

    @abc.abstractmethod
    async def count(self):
        pass

    @abc.abstractmethod
    async def scalars(self):
        pass

    @abc.abstractmethod
    def filter(self, **kwargs):
        pass

    @abc.abstractmethod
    def exclude(self, **kwargs):
        pass

    @abc.abstractmethod
    def limit(self, limit: int | None = None):
        pass

    @abc.abstractmethod
    def offset(self, offset: int | None = None):
        pass

    @abc.abstractmethod
    def order_by(self, **kwargs):
        pass

    @abc.abstractmethod
    def load_related(self, *loadings):
        pass
