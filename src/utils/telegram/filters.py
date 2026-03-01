import enum
import re
import typing

from telegram import Message
from telegram.ext._utils.types import FilterDataDict
from telegram.ext.filters import MessageFilter

ArgumentContext = dict[str, typing.Any]
ParameterType = tuple[type, str]
ArgumentMetadata = tuple["ArgumentTypeEnum", ParameterType | None]

COMMAND_REGEX = re.compile(r"/[\da-z_]{1,32}")


class ArgumentTypeEnum(str, enum.Enum):
    STRING = "string"
    PARAMETER = "parameter"


# TODO: tests
class ArgumentParser:
    _PARAMETER_SEPARATOR = ":"
    _PARAMETER_BEGIN = "<"
    _PARAMETER_END = ">"

    _MAP_PARAMETER_CLS = {
        "int": int,
        "float": float,
        "str": str,
    }

    def __init__(self, args: typing.Sequence[str]) -> None:
        self._args = args
        self._metadata = self._parse_args(args)

    @staticmethod
    def _list_args(text: str | typing.Sequence[str]) -> typing.Sequence[str]:
        args: typing.Sequence[str]

        if isinstance(text, str):
            args = text.split()
        elif isinstance(text, typing.Sequence):
            args = text
        else:
            raise ValueError(f"Unexpected text type: {type(text)}")

        return args

    def parse(self, text: str | typing.Sequence[str]) -> ArgumentContext | None:
        """
        Returns arguments context. Extracts and parses parameters from text.
        """
        words = self._list_args(text)

        if len(words) != len(self._args):
            return None

        context: ArgumentContext = {}
        for arg, word in zip(self._args, words):
            arg_type, metadata = self._metadata[arg]

            if arg_type is ArgumentTypeEnum.STRING:
                continue

            if metadata is None:
                raise ValueError(f"For parameter {arg} must be set metadata.")

            cls, arg_name = metadata
            context[arg_name] = cls(word)

        return context

    def _parse_parameter(self, parameter: str) -> ParameterType:
        type_, arg_name = parameter[1:-1].split(self._PARAMETER_SEPARATOR)
        cls = self._MAP_PARAMETER_CLS.get(type_)
        if cls is None:
            expected_types = ", ".join(self._MAP_PARAMETER_CLS.keys())
            raise ValueError(f"Unexpected type {type_}. Expected one of {expected_types}.")

        return cls, arg_name

    def _parse_args(self, args: typing.Sequence[str]) -> dict[str, ArgumentMetadata]:
        metadata: dict[str, ArgumentMetadata] = {}

        for arg in args:
            arg_type = self._get_arg_type(arg)

            match arg_type:
                case ArgumentTypeEnum.STRING:
                    metadata[arg] = (arg_type, None)
                case ArgumentTypeEnum.PARAMETER:
                    cls, arg_name = self._parse_parameter(arg)
                    metadata[arg] = (arg_type, (cls, arg_name))
                case _:
                    typing.assert_never(arg)

        return metadata

    def _validate_parameter(self, parameter: str) -> bool:
        if not parameter:
            return False

        return (
            parameter[0] == self._PARAMETER_BEGIN
            and parameter[-1] == self._PARAMETER_END
            and self._PARAMETER_SEPARATOR in parameter
        )

    def _get_arg_type(self, arg: str) -> ArgumentTypeEnum:
        if not arg:
            raise ValueError(f"Unexpected argument value: {arg}")

        if self._validate_parameter(arg):
            return ArgumentTypeEnum.PARAMETER

        return ArgumentTypeEnum.STRING

    def validate(self, text: str | typing.Sequence[str]) -> bool:
        words = self._list_args(text)

        if len(words) != len(self._args):
            return False

        for arg, word in zip(self._args, words):
            arg_type, metadata = self._metadata[arg]

            match arg_type:
                case ArgumentTypeEnum.PARAMETER:
                    if metadata is None:
                        raise ValueError(f"For parameter {arg} must be set metadata.")

                    cls, _ = metadata

                    try:
                        cls(word)
                    except Exception:
                        return False
                case ArgumentTypeEnum.STRING:
                    if arg != word:
                        return False
                case _:
                    typing.assert_never(arg_type)

        return True


class CommandArgumentsFilter(MessageFilter):
    def __init__(self, args: typing.Sequence[str]) -> None:
        super().__init__()

        self._args = args
        self.arg_parser = ArgumentParser(self._args)

    def filter(self, message: Message) -> bool | FilterDataDict | None:
        # remove command prefix from the message
        text = message.text
        if not text:
            return False

        match = COMMAND_REGEX.match(text)
        if not match:
            return False

        command = match.group(0)
        text = text.removeprefix(command).lstrip()

        return self.arg_parser.validate(text)
