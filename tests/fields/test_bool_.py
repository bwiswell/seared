from __future__ import annotations

import pytest

import seared as s


class TestBool:
    def test_load_and_dump(self):
        @s.seared
        class Obj(s.Seared):
            flag: bool = s.Bool(required=True)

        obj = Obj.load({'flag': True})
        assert obj.flag is True
        assert Obj.dump(obj) == {'flag': True}

    def test_false_value_preserved_in_dump(self):
        @s.seared
        class Obj(s.Seared):
            flag: bool = s.Bool(required=True)

        d = Obj.dump(Obj(flag=False))
        assert d['flag'] is False

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            flags: list = s.Bool(many=True, required=True)

        obj = Obj.load({'flags': [True, False, True]})
        assert obj.flags == [True, False, True]
        assert Obj.dump(obj) == {'flags': [True, False, True]}


class TestBoolSpellings:
    """Strict and lax read the same spellings; they differ only on the rest."""

    @pytest.mark.parametrize('validate', [True, False])
    @pytest.mark.parametrize('raw', ['true', ' Yes ', 'ON', '1'])
    def test_true_spellings(self, validate, raw):
        assert s.Bool().deserialize(raw, validate=validate) is True

    @pytest.mark.parametrize('validate', [True, False])
    @pytest.mark.parametrize('raw', ['false', ' No ', 'OFF', '0'])
    def test_false_spellings(self, validate, raw):
        assert s.Bool().deserialize(raw, validate=validate) is False

    def test_strict_rejects_unrecognised_strings(self):
        with pytest.raises(s.ValidationError, match="cannot deserialize 'maybe' as bool"):
            s.Bool().deserialize('maybe')

    @pytest.mark.parametrize(('raw', 'want'), [('maybe', True), ('', False), (2, True), (0, False), ([], False)])
    def test_lax_falls_back_to_truthiness(self, raw, want):
        assert s.Bool().deserialize(raw, validate=False) is want

    def test_lax_class_reads_false_through_load(self):
        # End to end, with whatever accelerator happens to be installed: a lax
        # Bool class stays on the Python path, so the fix can't be bypassed.
        @s.seared(validate=False)
        class Lax(s.Seared):
            flag: bool = s.Bool(required=True)

        assert Lax.load({'flag': 'false'}).flag is False
        assert Lax.load({'flag': 'off'}).flag is False
