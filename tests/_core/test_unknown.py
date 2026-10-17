"""Tests for ``seared._core.unknown`` — ``unknown_keys``, the report of every key
a wire dict holds that its class doesn't declare, and the refusal built on it."""

from __future__ import annotations

import functools
import operator

import pytest

import seared as s
from seared._core.unknown import check_unknown, refuse_unknown_keys, unknown_keys


@s.seared
class Latest(s.Seared):
    key: list = s.Str(many=True, default_factory=list)
    retention: str | None = s.Str(default=None)


@s.seared
class Stream(s.Seared):
    cls: str = s.Str(required=True)
    retention: str | None = s.Str(default=None)
    latest: Latest | None = s.T(Latest, default=None)


@s.seared
class Config(s.Seared):
    identity: str = s.Str(required=True)
    db_path: str = s.Str(default='chronicle.db', data_key='db-path')
    streams: list = s.T(Stream, many=True, default_factory=list)
    named: dict = s.T(Stream, keyed=True, default_factory=dict)
    zenoh: dict = s.Dict(default_factory=dict)
    pair: tuple | None = s.Tuple(s.Str(), s.T(Latest), default=None)


@s.seared
class Start(s.Seared):
    speed: int = s.Int(default=0)


@s.seared
class Stop(s.Seared):
    reason: str = s.Str(default='')


@s.seared
class Generic(s.Seared):
    pass


@s.seared
class Nested(s.Seared):
    id: int = s.Int(required=True)
    cmd: Start | Stop = s.Union(variants={'start': Start, 'stop': Stop}, tag_key='action', payload_key='args')


@s.seared
class Flat(s.Seared):
    id: int = s.Int(required=True)
    cmd: Start | Stop = s.Union(variants={'start': Start, 'stop': Stop})


@s.seared
class Tolerant(s.Seared):
    id: int = s.Int(required=True)
    cmd: Start | Stop | Generic = s.Union(variants={'start': Start, 'stop': Stop}, payload_key='args', fallback=Generic)


@s.seared
class TolerantFlat(s.Seared):
    id: int = s.Int(required=True)
    cmd: Start | Stop | Generic = s.Union(variants={'start': Start, 'stop': Stop}, fallback=Generic)


class TestTopLevel:
    def test_every_key_known_reports_nothing(self):
        assert unknown_keys(Config, {'identity': 'c1', 'db-path': 'x.db'}) == []

    def test_an_unknown_key_is_reported(self):
        assert unknown_keys(Config, {'identity': 'c1', 'identty': 'c2'}) == [('identty',)]

    def test_known_keys_are_wire_keys(self):
        # ``db_path`` is the attribute; on the wire it's ``db-path``.
        assert unknown_keys(Config, {'identity': 'c1', 'db_path': 'x.db'}) == [('db_path',)]

    def test_paths_come_in_the_inputs_order(self):
        data = {'zz': 1, 'identity': 'c1', 'aa': 2, 'mm': 3}
        assert unknown_keys(Config, data) == [('zz',), ('aa',), ('mm',)]

    def test_a_null_value_on_a_known_key_is_not_walked(self):
        assert unknown_keys(Config, {'identity': 'c1', 'streams': None, 'pair': None}) == []

    def test_data_that_isnt_a_dict_has_nothing_to_report(self):
        assert unknown_keys(Config, ['identity']) == []
        assert unknown_keys(Config, None) == []

    def test_a_class_that_isnt_seared_is_refused(self):
        class Plain:
            pass

        with pytest.raises(TypeError, match='not a @seared class'):
            unknown_keys(Plain, {})

    def test_the_input_is_left_alone(self):
        data = {'identity': 'c1', 'extra': {'x': 1}}
        unknown_keys(Config, data)
        assert data == {'identity': 'c1', 'extra': {'x': 1}}

    def test_re_exported_at_the_package_root(self):
        assert s.unknown_keys is unknown_keys


class TestNested:
    def test_a_t_target_is_walked(self):
        data = {'identity': 'c1', 'streams': [{'cls': 'a:B', 'latest': {'key': ['id'], 'retension': '30d'}}]}
        assert unknown_keys(Config, data) == [('streams', 0, 'latest', 'retension')]

    def test_each_element_of_a_many_field(self):
        data = {'identity': 'c1', 'streams': [{'cls': 'a:A'}, {'cls': 'a:B', 'retension': '7d'}, {'clss': 'a:C'}]}
        assert unknown_keys(Config, data) == [('streams', 1, 'retension'), ('streams', 2, 'clss')]

    def test_each_value_of_a_keyed_field(self):
        data = {'identity': 'c1', 'named': {'north': {'cls': 'a:A', 'oops': 1}}}
        assert unknown_keys(Config, data) == [('named', 'north', 'oops')]

    def test_a_tuple_slot_is_walked(self):
        data = {'identity': 'c1', 'pair': ['x', {'key': ['id'], 'retension': '1d'}]}
        assert unknown_keys(Config, data) == [('pair', 1, 'retension')]

    def test_a_dict_fields_keys_are_data_not_schema(self):
        assert unknown_keys(Config, {'identity': 'c1', 'zenoh': {'mode': 'peer', 'anything': 1}}) == []

    def test_depth_first_in_the_inputs_order(self):
        data = {'a': 1, 'identity': 'c1', 'streams': [{'cls': 'x', 'b': 2}], 'c': 3}
        assert unknown_keys(Config, data) == [('a',), ('streams', 0, 'b'), ('c',)]

    def test_each_path_retrieves_the_value_under_it(self):
        data = {
            'identity': 'c1',
            'streams': [{'cls': 'x', 'latest': {'oops': 42}}],
            'named': {'n': {'cls': 'y', 'k': 7}},
        }
        values = [functools.reduce(operator.getitem, path, data) for path in unknown_keys(Config, data)]
        assert values == [42, 7]


class TestUnionEnvelopes:
    def test_a_nested_envelopes_keys_are_known_and_its_payload_walked(self):
        data = {'id': 1, 'action': 'start', 'args': {'speed': 3, 'sped': 4}}
        assert unknown_keys(Nested, data) == [('args', 'sped')]

    def test_a_flat_envelope_knows_the_selected_variants_keys(self):
        assert unknown_keys(Flat, {'id': 1, 'type': 'start', 'speed': 3}) == []
        assert unknown_keys(Flat, {'id': 1, 'type': 'start', 'reason': 'x'}) == [('reason',)]

    def test_a_nested_envelope_with_an_unknown_tag_still_reports_its_parents_keys(self):
        # ``load`` refuses the tag; the payload belongs to no declared variant, so it isn't walked.
        data = {'id': 1, 'action': 'jump', 'args': {'height': 3}, 'oops': 1}
        assert unknown_keys(Nested, data) == [('oops',)]

    def test_a_flat_envelope_with_an_unknown_tag_reports_nothing_at_its_level(self):
        # Its variant's keys sit beside the parent's, and no declared variant says which they are.
        assert unknown_keys(Flat, {'id': 1, 'type': 'jump', 'height': 3}) == []
        assert unknown_keys(Flat, {'id': 1, 'height': 3}) == []

    def test_a_payload_routed_to_the_fallback_is_not_checked(self):
        assert unknown_keys(Tolerant, {'id': 1, 'type': 'jump', 'args': {'height': 3}}) == []
        assert unknown_keys(TolerantFlat, {'id': 1, 'type': 'jump', 'height': 3}) == []

    def test_a_known_tag_under_a_fallback_union_is_still_checked(self):
        assert unknown_keys(Tolerant, {'id': 1, 'type': 'stop', 'args': {'reasn': 'x'}}) == [('args', 'reasn')]


class TestRefusal:
    def test_nothing_unknown_refuses_nothing(self):
        assert refuse_unknown_keys(Config, {'identity': 'c1'}) is None

    def test_one_unknown_key(self):
        with pytest.raises(s.ValidationError) as caught:
            refuse_unknown_keys(Config, {'identity': 'c1', 'identty': 'c2'})
        err = caught.value
        assert (err.reason, err.path, err.cls_name) == ('unknown key', ('identty',), 'Config')
        assert str(err) == 'Config.identty: unknown key'

    def test_the_first_is_the_path_and_the_rest_are_named(self):
        data = {'identity': 'c1', 'streams': [{'cls': 'x', 'retension': '7d'}], 'zenoh': {}, 'oops': 1}
        with pytest.raises(s.ValidationError) as caught:
            refuse_unknown_keys(Config, data)
        assert caught.value.path == ('streams', 0, 'retension')
        assert str(caught.value) == 'Config.streams[0].retension: unknown key (1 more: oops)'

    def test_past_five_more_the_rest_are_counted(self):
        data = {'identity': 'c1', **{f'k{i}': i for i in range(8)}}
        with pytest.raises(s.ValidationError) as caught:
            refuse_unknown_keys(Config, data)
        assert caught.value.reason == 'unknown key (7 more: k1, k2, k3, k4, k5, …)'

    def test_only_ignore_and_raise_are_options(self):
        check_unknown('ignore', 'here')
        check_unknown('raise', 'here')
        with pytest.raises(ValueError, match="here: unknown= takes 'ignore' or 'raise', got 'strict'"):
            check_unknown('strict', 'here')
