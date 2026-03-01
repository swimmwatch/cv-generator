import abc


class BaseSpecification(abc.ABC):
    @abc.abstractmethod
    async def is_satisfied(self, **kwargs) -> bool:
        raise NotImplementedError

    async def __call__(self, **kwargs) -> bool:
        return await self.is_satisfied(**kwargs)

    def __and__(self, other: "BaseSpecification"):
        return AndBaseSpecification(self, other)

    def __or__(self, other: "BaseSpecification"):
        return OrBaseSpecification(self, other)

    def __invert__(self):
        return NotBaseSpecification(self)


class LogicBaseSpecification(BaseSpecification, abc.ABC):
    def __init__(self, *args):
        self.args = args


class AndBaseSpecification(LogicBaseSpecification):
    async def is_satisfied(self, **kwargs) -> bool:
        for perm in self.args:
            if not await perm.is_satisfied(**kwargs):
                return False
        return True


class OrBaseSpecification(LogicBaseSpecification):
    async def is_satisfied(self, **kwargs) -> bool:
        for perm in self.args:
            if await perm.is_satisfied(**kwargs):
                return True
        return False


class NotBaseSpecification(LogicBaseSpecification):
    async def is_satisfied(self, **kwargs) -> bool:
        perm = self.args[0]
        return not await perm.is_satisfied(**kwargs)
