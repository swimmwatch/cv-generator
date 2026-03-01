import secrets
import typing

import pytest

from utils.iter import compare_changes
from utils.iter import random_switch_case
from utils.iter import random_switch_case_gen


def _object_factory(fields: dict[str, typing.Any]) -> object:
    """
    Create an object with the given fields.
    """

    class Object:
        pass

    obj = Object()
    for field, value in fields.items():
        setattr(obj, field, value)

    return obj


class TestCompareChanges:
    @pytest.mark.parametrize(
        (
            "source",
            "target",
            "fields",
            "expected",
        ),
        [
            (
                _object_factory({"field": 1}),
                _object_factory({"field": 1}),
                ["field"],
                (False, {}),
            ),
            (
                _object_factory({"field": 1}),
                _object_factory({"field": 2}),
                ["field"],
                (True, {"field": 2}),
            ),
        ],
    )
    def test_success(
        self,
        source: object,
        target: object,
        fields: typing.Iterable[str],
        expected: tuple[bool, dict[str, typing.Any]],
    ) -> None:
        actual = compare_changes(source, target, fields)
        assert actual == expected


class TestRandomSwitchCase:
    def test_empty_string(self):
        assert random_switch_case("") == ""

    def test_non_string_input_gen(self):
        with pytest.raises(TypeError):
            list(random_switch_case_gen(123))  # type: ignore[arg-type]

    def test_non_string_input_func(self):
        with pytest.raises(TypeError):
            random_switch_case(123)  # type: ignore[arg-type]

    def test_non_alpha_characters_unchanged(self, monkeypatch):
        # Force deterministic outcome (always choose lower) though it shouldn't matter
        monkeypatch.setattr(secrets, "randbits", lambda n: 1)
        s = "1234-=_+!? 🤖🚀"
        assert random_switch_case(s) == s

    def test_multi_codepoint_mapping_preserved(self, monkeypatch):
        # 'ß'.upper() -> 'SS' (length 2); should remain 'ß'
        monkeypatch.setattr(secrets, "randbits", lambda n: 1)
        s = "ßa"
        out = random_switch_case(s)
        assert len(out) == len(s)
        assert out[0] == "ß"  # unchanged
        assert out[1] in {"a", "A"}

    def test_deterministic_toggle_pattern(self, monkeypatch):
        # Create a predictable sequence: 1,0,1,0,... so we can assert output
        pattern = [1, 0]
        state = {"i": 0}

        def fake(n: int) -> int:
            val = pattern[state["i"] % len(pattern)]
            state["i"] += 1
            return val

        monkeypatch.setattr(secrets, "randbits", fake)
        s = "AbCdE"
        # randbits=1 -> lower, randbits=0 -> upper per implementation
        # So pattern yields: lower, UPPER, lower, UPPER, lower
        expected = [
            s[0].lower(),
            s[1].upper(),
            s[2].lower(),
            s[3].upper(),
            s[4].lower(),
        ]
        assert random_switch_case(s) == "".join(expected)

    def test_unicode_letters_length_preserved(self, monkeypatch):
        # Mix of Greek, Latin; ensure length stable & chars are case variants
        monkeypatch.setattr(secrets, "randbits", lambda n: 1)
        s = "ΑλφαBetaΓΔ"  # mixture
        out = random_switch_case(s)
        assert len(out) == len(s)
        for original, new in zip(s, out):
            if original.lower() == original.upper():  # non-cased (unlikely here)
                assert original == new
            else:
                # Should be either lower or upper (we forced lower with randbits->1)
                assert new in {original.lower(), original.upper()}
