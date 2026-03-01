import typing
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from telegram import Update
from telegram._utils.types import RT
from telegram._utils.types import SCT
from telegram.ext import CommandHandler
from telegram.ext._utils.types import CCT
from telegram.ext._utils.types import HandlerCallback

from utils.telegram.context import CustomContext
from utils.telegram.filters import CommandArgumentsFilter

if typing.TYPE_CHECKING:
    from telegram.ext import Application


class CommandWithArgsHandler(CommandHandler):
    def __init__(
        self,
        command: SCT[str],
        args: typing.Sequence[str],
        callback: HandlerCallback[Update, CCT, RT],
    ):
        filters = CommandArgumentsFilter(args)

        super().__init__(command, callback, filters)

        self._arg_parser = filters.arg_parser

    def collect_additional_context(
        self,
        context: CustomContext,
        update: Update,  # skipcq: BAN-B301
        application: "Application[typing.Any, CCT, typing.Any, typing.Any, typing.Any, typing.Any]",  # skipcq: BAN-B301
        check_result: Optional[Union[bool, Tuple[List[str], Optional[bool]]]],
    ) -> None:
        if isinstance(check_result, tuple):
            args, _ = check_result
            kwargs = self._arg_parser.parse(args)

            if kwargs:
                context.kwargs = kwargs
            else:
                context.kwargs = {}
