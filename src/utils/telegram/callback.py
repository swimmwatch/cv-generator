import typing

T = typing.TypeVar("T", str, int)


def get_postfix(query_data: str, base_prefix: str, default="", factory=str):
    pattern_prefix_length = len(base_prefix)
    postfix = query_data[pattern_prefix_length:]
    if not postfix:
        return default

    return factory(query_data[pattern_prefix_length:])
