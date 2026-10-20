from __future__ import annotations

import re

import pytest

import seared as s


class TestStr:
    @pytest.fixture
    def cls(self):
        @s.seared
        class Obj(s.Seared):
            name: str = s.Str(required=True)
            alias: str | None = s.Str(data_key='alias_key')

        return Obj

    def test_load(self, cls):
        obj = cls.load({'name': 'Alice', 'alias_key': 'Al'})
        assert obj.name == 'Alice'
        assert obj.alias == 'Al'

    def test_dump(self, cls):
        d = cls.dump(cls(name='Alice', alias='Al'))
        assert d == {'name': 'Alice', 'alias_key': 'Al'}

    def test_missing_optional_absent_from_dump(self, cls):
        d = cls.dump(cls(name='Bob', alias=None))
        assert 'alias_key' not in d

    def test_data_key_used_for_load(self, cls):
        obj = cls.load({'name': 'X', 'alias_key': 'Y'})
        assert obj.alias == 'Y'

    def test_data_key_used_for_dump(self, cls):
        d = cls.dump(cls(name='X', alias='Y'))
        assert 'alias_key' in d
        assert 'alias' not in d

    def test_many_load(self):
        @s.seared
        class Obj(s.Seared):
            tags: list = s.Str(many=True, required=True)

        obj = Obj.load({'tags': ['a', 'b', 'c']})
        assert obj.tags == ['a', 'b', 'c']

    def test_many_dump(self):
        @s.seared
        class Obj(s.Seared):
            tags: list = s.Str(many=True, required=True)

        d = Obj.dump(Obj(tags=['a', 'b', 'c']))
        assert d == {'tags': ['a', 'b', 'c']}

    def test_keyed_load(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Str(keyed=True, required=True)

        obj = Obj.load({'mapping': {'x': 'hello', 'y': 'world'}})
        assert obj.mapping == {'x': 'hello', 'y': 'world'}

    def test_keyed_dump(self):
        @s.seared
        class Obj(s.Seared):
            mapping: dict = s.Str(keyed=True, required=True)

        d = Obj.dump(Obj(mapping={'x': 'hello', 'y': 'world'}))
        assert d == {'mapping': {'x': 'hello', 'y': 'world'}}


class TestTypes:
    """Pin: an exact ``str`` takes a fast path (0.4.4) that answers as the full one did."""

    def test_a_subclass_loads_as_itself(self):
        class Name(str):
            __slots__ = ()

        assert type(s.Str().deserialize(Name('x'))) is Name

    @pytest.mark.parametrize('method', ['deserialize', 'serialize'])
    def test_a_non_string_is_refused_strict(self, method):
        with pytest.raises(s.ValidationError, match=r'^expected str, got int$'):
            getattr(s.Str(), method)(5)

    def test_a_non_string_is_read_lax(self):
        assert s.Str().deserialize(5, validate=False) == '5'


@s.seared
class Code(s.Seared):
    code: str = s.Str(min_length=2, max_length=4, default='ab')
    names: list[str] = s.Str(min_length=1, many=True, default_factory=list)
    by_id: dict[str, str] = s.Str(max_length=3, keyed=True, default_factory=dict)


@s.seared(validate=False)
class LaxCode(s.Seared):
    code: str = s.Str(min_length=2, default='ab')


class TestLengths:
    """Pin: lengths count code points, on a strict load and a strict dump (0.4.4)."""

    @pytest.mark.parametrize(
        ('options', 'inside', 'outside', 'reason'),
        [
            ({'min_length': 2}, 'ab', 'a', 'must be at least 2 characters long, got 1'),
            ({'min_length': 1}, 'a', '', 'must be at least 1 character long, got 0'),
            ({'max_length': 3}, 'abc', 'abcd', 'must be at most 3 characters long, got 4'),
            ({'max_length': 0}, '', 'a', 'must be at most 0 characters long, got 1'),
        ],
    )
    def test_each_option(self, options, inside, outside, reason):
        field = s.Str(**options)
        assert field.deserialize(inside) == inside
        assert field.serialize(inside) == inside
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.deserialize(outside)
        with pytest.raises(s.ValidationError, match=f'^{re.escape(reason)}$'):
            field.serialize(outside)

    def test_a_length_counts_code_points(self):
        # As JSON Schema counts characters; JavaScript's ``.length`` would say 8.
        assert Code.load({'code': '😀😀😀😀'}).code == '😀😀😀😀'
        with pytest.raises(s.ValidationError, match=r'^Code\.code: must be at most 4 characters long, got 5$'):
            Code.load({'code': '😀😀😀😀😀'})

    def test_a_dump_refuses_a_constructed_value_outside_them(self):
        with pytest.raises(s.ValidationError, match=r'^Code\.code: must be at least 2 characters long, got 1$'):
            Code.dump(Code(code='a'))

    def test_a_many_element_is_named_by_its_index(self):
        with pytest.raises(s.ValidationError, match=r'^Code\.names\[1\]: must be at least 1 character long, got 0$'):
            Code.load({'names': ['ok', '']})

    def test_a_keyed_value_is_named_by_its_key(self):
        with pytest.raises(s.ValidationError, match=r"^Code\.by_id\['r-1'\]: must be at most 3 characters long"):
            Code.load({'by_id': {'r-0': 'abc', 'r-1': 'abcd'}})

    def test_lax_mode_skips_them(self):
        assert LaxCode.load({'code': 'a'}).code == 'a'
        assert LaxCode.dump(LaxCode(code='a')) == {'code': 'a'}

    def test_the_reduced_checks_stay_out_of_equality_and_repr(self):
        assert s.Str(min_length=1) == s.Str(min_length=1)
        assert s.Str(min_length=1) != s.Str(min_length=2)
        assert '_checks' not in repr(s.Str(min_length=1))
