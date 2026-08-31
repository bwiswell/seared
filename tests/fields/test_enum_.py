from __future__ import annotations

import pytest
from conftest import Color, Status

import seared as s


class TestEnum:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            color: Color = s.Enum(enum=Color, required=True)
            optional_color: Color | None = s.Enum(enum=Color, missing=Color.RED)

        return Obj

    def test_load(self, cls):
        obj = cls.load({'color': 2})
        assert obj.color == Color.BLUE

    def test_load_string_value(self, cls):
        obj = cls.load({'color': '1'})
        assert obj.color == Color.GREEN

    def test_dump(self, cls):
        d = cls.dump(cls(color=Color.BLUE, optional_color=Color.GREEN))
        assert d['color'] == 2
        assert d['optional_color'] == 1

    def test_missing_default(self, cls):
        obj = cls.load({'color': 0})
        assert obj.optional_color == Color.RED

    def test_optional_none_excluded_from_dump(self):
        @s.seared
        class Obj(s.Seared):
            color: Color | None = s.Enum(enum=Color)

        d = Obj.dump(Obj(color=None))
        assert 'color' not in d

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        obj = Obj.load({'colors': [0, 1, 2]})
        assert obj.colors == [Color.RED, Color.GREEN, Color.BLUE]

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        obj = Obj(colors=[Color.RED, Color.GREEN, Color.BLUE])
        d = Obj.dump(obj)
        assert d == {'colors': [0, 1, 2]}

    def test_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            colors: list = s.Enum(enum=Color, many=True, required=True)

        raw = {'colors': [2, 0, 1]}
        obj = Obj.load(raw)
        assert Obj.dump(obj) == raw

    def test_keyed_load(self):
        @s.seared
        class Obj(s.Seared):
            palette: dict = s.Enum(enum=Color, keyed=True, required=True)

        obj = Obj.load({'palette': {'bg': 0, 'fg': 2}})
        assert obj.palette == {'bg': Color.RED, 'fg': Color.BLUE}

    def test_keyed_dump(self):
        @s.seared
        class Obj(s.Seared):
            palette: dict = s.Enum(enum=Color, keyed=True, required=True)

        obj = Obj(palette={'bg': Color.RED, 'fg': Color.BLUE})
        d = Obj.dump(obj)
        assert d == {'palette': {'bg': 0, 'fg': 2}}

    def test_str_enum_load(self):
        @s.seared
        class Obj(s.Seared):
            status: Status = s.Enum(enum=Status, required=True)

        obj = Obj.load({'status': 'active'})
        assert obj.status == Status.ACTIVE

    def test_str_enum_dump(self):
        @s.seared
        class Obj(s.Seared):
            status: Status = s.Enum(enum=Status, required=True)

        d = Obj.dump(Obj(status=Status.PENDING))
        assert d == {'status': 'pending'}

    def test_str_enum_missing_default(self):
        @s.seared
        class Obj(s.Seared):
            status: Status | None = s.Enum(enum=Status, missing=Status.INACTIVE)

        obj = Obj.load({})
        assert obj.status == Status.INACTIVE

    def test_str_enum_many_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            statuses: list = s.Enum(enum=Status, many=True, required=True)

        raw = {'statuses': ['active', 'pending', 'inactive']}
        obj = Obj.load(raw)
        assert obj.statuses == [Status.ACTIVE, Status.PENDING, Status.INACTIVE]
        assert Obj.dump(obj) == raw

    def test_str_enum_keyed_round_trip(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Enum(enum=Status, keyed=True, required=True)

        raw = {'mapping': {'a': 'active', 'b': 'pending'}}
        obj = Obj.load(raw)
        assert obj.mapping == {'a': Status.ACTIVE, 'b': Status.PENDING}
        assert Obj.dump(obj) == raw
