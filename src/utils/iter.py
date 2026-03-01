import secrets
import typing


def compare_changes(source: object, target: object, fields: typing.Iterable[str]) -> tuple[bool, dict[str, typing.Any]]:
    """
    Compare changes between two objects.
    """
    changes = {}
    has_changes = False
    for field in fields:
        source_value = getattr(source, field, None)
        target_value = getattr(target, field, None)
        if source_value != target_value:
            changes[field] = target_value
            has_changes = True

    return has_changes, changes


def random_switch_case_gen(s: str) -> typing.Iterator[str]:
    """Yield characters of ``s`` with randomly switched case.

    Rules / corner cases handled:
    - If ``s`` is not a ``str``: ``TypeError`` is raised (fail fast).
    - Characters without case (digits, punctuation, symbols) are yielded unchanged.
    - For characters whose upper/lower conversion changes length (e.g. German 'ß' -> 'SS'),
    the original character is yielded to preserve positional mapping and overall length.
    - Unicode case-folding that does not alter code point count is respected (e.g. Greek letters, Latin letters).
    - Randomness: each eligible character has a 50% chance to become lower vs upper using ``secrets.randbits(1)``.
    - The generator is lazy; consuming code can short‑circuit without building the whole string.
    """
    if not isinstance(s, str):  # Explicit type guard to surface misuse early
        raise TypeError("random_switch_case_gen expects a str input")

    for ch in s:
        # Quick path: characters with identical upper/lower (no case) stay unchanged.
        lower = ch.lower()
        upper = ch.upper()
        if lower == upper:
            yield ch
            continue

        # If any transformation expands into multiple code points, keep original to avoid length skew.
        # Example: 'ß'.upper() -> 'SS'. We don't want output length to differ unpredictably.
        if len(lower) != 1 or len(upper) != 1:
            yield ch
            continue

        # Randomly choose lower or upper variant.
        yield lower if secrets.randbits(1) else upper


def random_switch_case(s: str) -> str:
    """Return a new string with randomly switched case for each character.

    See ``random_switch_case_gen`` for detailed behavior & corner cases.

    Guarantees:
    - Output length equals input length.
    - Non-alphabetic characters are unchanged.
    - Characters with multi-codepoint case mappings remain unchanged.
    - Raises ``TypeError`` if input is not a ``str``.
    """
    return "".join(random_switch_case_gen(s))
