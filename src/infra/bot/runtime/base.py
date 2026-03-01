import abc


class PTBRunner(abc.ABC):
    @abc.abstractmethod
    async def start(self):
        pass

    @abc.abstractmethod
    async def stop(self):
        pass
