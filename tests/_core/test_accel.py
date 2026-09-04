"""Tests for ``seared._core.accel`` — the optional-accelerator seam.

Three layers:

- ``TestBackendResolution`` / ``TestModes`` — the handshake and the env vars,
  including what happens with no backend at all (the default for every user
  who never installs one).
- ``TestClassDecisions`` / ``TestSpecEmission`` — which classes are
  accelerable, why the rest aren't, and the plain-data spec handed over.
- ``TestDifferential`` — the contract itself: an accelerated class and a
  pure-Python one must agree on every value *and* every error message.
  ``refcore`` stands in for `rusted` until it exists.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
import refcore

import seared as s
from seared._core import accel


@pytest.fixture
def use_backend(monkeypatch):
    """Point seared at a named backend (or none) and drop the cached lookup."""

    def _use(name=None, mode=None):
        if name is None:
            monkeypatch.delenv(accel.BACKEND_ENV, raising=False)
        else:
            monkeypatch.setenv(accel.BACKEND_ENV, name)
        if mode is None:
            monkeypatch.delenv(accel.MODE_ENV, raising=False)
        else:
            monkeypatch.setenv(accel.MODE_ENV, mode)
        accel._reset()

    yield _use
    accel._reset()


#: Stands in for "no backend available". Deliberately not "just don't set the
#: env var": `rusted` may well be installed in the environment running these
#: tests, and a fixture that assumed otherwise would quietly stop testing the
#: unavailable path the moment it was.
MISSING = 'seared_no_such_backend'


def _tier1(**kwargs):
    """The bench schema — the canonical fully-accelerable shape."""

    @s.seared(**kwargs)
    class Inner(s.Seared):
        x: int = s.Int(required=True)
        y: float = s.Float(required=True)
        label: str | None = s.Str(default=None)

    @s.seared(**kwargs)
    class Outer(s.Seared):
        name: str = s.Str(required=True)
        flag: bool = s.Bool(default=False)
        items: list[Inner] = s.T(Inner, many=True, required=True)
        tags: list[str] = s.Str(many=True, default_factory=list)

    return Inner, Outer


PAYLOAD = {
    'name': 'demo',
    'flag': True,
    'items': [{'x': i, 'y': i * 1.5, 'label': f'i{i}'} for i in range(3)],
    'tags': ['alpha', 'beta'],
}


# ---------------------------------------------------------------------------
# Backend resolution + handshake
# ---------------------------------------------------------------------------


class TestBackendResolution:
    def test_unavailable_backend_reports_why(self, use_backend):
        use_backend(MISSING)
        status = accel.accel_status()
        assert status['available'] is False
        assert status['backend'] is None
        assert MISSING in status['reason']

    def test_rusted_is_the_default_backend_name(self):
        # Asserted on the constant, not on an import: whether rusted is
        # installed in *this* environment is not what's under test.
        assert accel.DEFAULT_BACKEND == 'rusted'

    def test_refcore_loads(self, use_backend):
        use_backend('refcore')
        status = accel.accel_status()
        assert status['available'] is True
        assert status['backend'] == 'refcore'
        assert status['reason'] is None
        assert status['spec_abi'] == accel.SPEC_ABI
        assert status['backend_version'] == '0.0.0'
        # Diagnostic only — never enforced.
        assert status['supports_seared'] == refcore.SUPPORTS_SEARED

    def test_missing_module_declines(self, use_backend):
        use_backend('no_such_accelerator_module')
        assert accel.accel_status()['available'] is False

    def test_abi_mismatch_declines(self, use_backend, monkeypatch):
        monkeypatch.setitem(
            sys.modules,
            'fake_accel',
            SimpleNamespace(SPEC_ABI=999, compile_spec=lambda spec: None),
        )
        use_backend('fake_accel')
        status = accel.accel_status()
        assert status['available'] is False
        assert 'SPEC_ABI 999' in status['reason']

    def test_missing_compile_spec_declines(self, use_backend, monkeypatch):
        monkeypatch.setitem(
            sys.modules,
            'fake_accel2',
            SimpleNamespace(SPEC_ABI=accel.SPEC_ABI),
        )
        use_backend('fake_accel2')
        assert 'compile_spec' in accel.accel_status()['reason']

    def test_backend_that_raises_is_never_fatal(self, use_backend, monkeypatch):
        def boom(spec):
            msg = 'backend exploded'
            raise RuntimeError(msg)

        monkeypatch.setitem(
            sys.modules,
            'fake_accel3',
            SimpleNamespace(SPEC_ABI=accel.SPEC_ABI, compile_spec=boom),
        )
        use_backend('fake_accel3')
        _inner, outer = _tier1()
        assert outer.__seared_accel__.accelerated is False
        assert 'backend exploded' in outer.__seared_accel__.reason
        # ...and the class still works.
        assert outer.dump(outer.load(PAYLOAD))['name'] == 'demo'

    def test_backend_returning_none_declines(self, use_backend, monkeypatch):
        monkeypatch.setitem(
            sys.modules,
            'fake_accel4',
            SimpleNamespace(SPEC_ABI=accel.SPEC_ABI, compile_spec=lambda spec: None),
        )
        use_backend('fake_accel4')
        _inner, outer = _tier1()
        assert outer.__seared_accel__.accelerated is False
        assert 'declined the spec' in outer.__seared_accel__.reason


class TestModes:
    def test_off_skips_an_available_backend(self, use_backend):
        use_backend('refcore', mode='off')
        _inner, outer = _tier1()
        assert outer.__seared_accel__.accelerated is False
        assert outer.__seared_accel__.reason == 'SEARED_ACCEL=off'

    def test_require_raises_when_no_backend(self, use_backend):
        use_backend(MISSING, mode='require')
        with pytest.raises(s.SearedError, match='require'):
            _tier1()

    def test_require_tolerates_a_class_declining(self, use_backend):
        # `require` asserts the *backend* loaded, not that every class is
        # accelerable — seared's own suite is full of classes no backend takes.
        # `Tuple` is deliberate: it is out of scope by design (per-slot
        # sub-fields), not merely unimplemented, so a future tier won't quietly
        # turn this into a test of nothing the way `Decimal` did.
        use_backend('refcore', mode='require')

        @s.seared
        class HasTuple(s.Seared):
            pair: tuple = s.Tuple(s.Int(), s.Str(), required=True)

        assert HasTuple.__seared_accel__.accelerated is False

    def test_unknown_mode_raises(self, use_backend):
        use_backend('refcore', mode='requrie')
        with pytest.raises(s.SearedError, match='must be one of'):
            accel.accel_status()


# ---------------------------------------------------------------------------
# Per-class accelerability
# ---------------------------------------------------------------------------


class TestClassDecisions:
    def test_tier1_class_is_accelerated(self, use_backend):
        use_backend('refcore')
        inner, outer = _tier1()
        assert inner.__seared_accel__.accelerated is True
        assert outer.__seared_accel__ == s.AccelInfo(accelerated=True, backend='refcore')

    def test_no_backend_means_no_acceleration(self, use_backend):
        use_backend(MISSING)
        _inner, outer = _tier1()
        assert outer.__seared_accel__.accelerated is False
        assert not hasattr(outer, '__seared_spec__')

    def test_unsupported_field_type_declines_and_names_it(self, use_backend):
        use_backend('refcore')

        @s.seared
        class HasTuple(s.Seared):
            ok: int = s.Int(required=True)
            pair: tuple = s.Tuple(s.Int(), s.Str(), required=True)

        reason = HasTuple.__seared_accel__.reason
        assert 'HasTuple.pair' in reason
        assert 'Tuple is not an accelerated field type' in reason

    def test_field_subclass_declines_exact_type_gate(self, use_backend):
        use_backend('refcore')

        class LoudInt(s.Int):
            def deserialize(self, value, validate=True, **kwargs):
                return super().deserialize(value, validate, **kwargs) * 2

        @s.seared
        class Custom(s.Seared):
            x: int = LoudInt(required=True)

        assert Custom.__seared_accel__.accelerated is False
        assert 'LoudInt' in Custom.__seared_accel__.reason
        # The override still runs — falling back is what protects it.
        assert Custom.load({'x': 5}).x == 10

    def test_post_init_declines(self, use_backend):
        use_backend('refcore')

        @s.seared
        class WithPostInit(s.Seared):
            x: int = s.Int(required=True)

            def __post_init__(self):
                pass

        assert WithPostInit.__seared_accel__.reason == 'class defines __post_init__'

    def test_custom_init_declines(self, use_backend):
        use_backend('refcore')

        @s.seared
        class WithInit(s.Seared):
            x: int = s.Int(required=True)

            def __init__(self, **kwargs):
                object.__setattr__(self, 'x', kwargs.get('x', 0))

        assert WithInit.__seared_accel__.reason == 'class defines its own __init__'

    def test_plain_dataclass_field_declines(self, use_backend):
        # ``b`` is a dataclass field but not a seared ``Field``, so it never
        # reaches the spec. The Python path still sets it — ``load`` runs
        # ``__init__`` — but a core constructing via ``__new__`` would leave
        # the slot unset, and ``repr`` / ``__eq__`` would raise on it.
        use_backend('refcore')

        @s.seared
        class Mixed(s.Seared):
            a: int = s.Int(required=True)
            b: int = 5

        info = Mixed.__seared_accel__
        assert info.accelerated is False
        assert info.reason == 'Mixed.b is a plain dataclass field, not a seared Field'
        obj = Mixed.load({'a': 1})
        assert (obj.a, obj.b) == (1, 5)
        assert obj == Mixed(a=1)

    def test_nested_declines_poison_the_parent(self, use_backend):
        use_backend('refcore')

        @s.seared
        class Leaf(s.Seared):
            pair: tuple = s.Tuple(s.Int(), s.Str(), required=True)

        @s.seared
        class Branch(s.Seared):
            leaf: Leaf = s.T(Leaf, required=True)

        reason = Branch.__seared_accel__.reason
        assert 'Branch.leaf →' in reason
        assert 'Leaf.pair' in reason

    def test_accel_false_opts_out(self, use_backend):
        use_backend('refcore')
        _inner, outer = _tier1(accel=False)
        assert outer.__seared_accel__.reason == 'accel=False on the decorator'

    def test_slots_false_still_accelerates(self, use_backend):
        use_backend('refcore')
        _inner, outer = _tier1(slots=False)
        assert outer.__seared_accel__.accelerated is True
        assert outer.dump(outer.load(PAYLOAD)) == PAYLOAD


class TestSpecEmission:
    def test_spec_shape(self, use_backend):
        use_backend('refcore')
        _inner, outer = _tier1()
        spec = outer.__seared_spec__
        assert spec['abi'] == accel.SPEC_ABI
        assert spec['cls'] is outer
        assert spec['name'] == 'Outer'
        assert spec['validate'] is True

        by_attr = {f['attr']: f for f in spec['fields']}
        assert by_attr['name']['kind'] == 'str'
        assert by_attr['name']['required'] is True
        assert by_attr['flag']['kind'] == 'bool'
        # ``default=`` is already folded into ``missing`` by Field.__post_init__.
        assert by_attr['flag']['default'] is False
        assert by_attr['tags']['many'] is True
        assert by_attr['tags']['default_factory'] is list
        assert by_attr['items']['kind'] == 'nested'
        assert by_attr['items']['schema']['name'] == 'Inner'

    def test_data_key_becomes_the_wire_key(self, use_backend):
        use_backend('refcore')

        @s.seared
        class Renamed(s.Seared):
            a: int = s.Int(data_key='propertyA', required=True)

        (field,) = Renamed.__seared_spec__['fields']
        assert (field['attr'], field['wire']) == ('a', 'propertyA')

    def test_flags_are_carried(self, use_backend):
        use_backend('refcore')

        @s.seared
        class Flags(s.Seared):
            keyed: dict[str, int] = s.Int(keyed=True)
            hidden: str | None = s.Str(dump=False)

        by_attr = {f['attr']: f for f in Flags.__seared_spec__['fields']}
        assert by_attr['keyed']['keyed'] is True
        assert by_attr['hidden']['dump'] is False

    def test_lax_class_carries_its_own_validate(self, use_backend):
        use_backend('refcore')
        _inner, outer = _tier1(validate=False)
        assert outer.__seared_spec__['validate'] is False
        assert outer.__seared_spec__['fields'][2]['schema']['validate'] is False


# ---------------------------------------------------------------------------
# The contract: accelerated and pure must be indistinguishable.
# ---------------------------------------------------------------------------

#: (label, payload) — valid and malformed, strict-mode.
CASES = [
    ('valid', PAYLOAD),
    ('missing-required', {'items': []}),
    ('int-from-str', {**PAYLOAD, 'items': [{'x': '7', 'y': 1.0}]}),
    ('int-from-float', {**PAYLOAD, 'items': [{'x': 7.9, 'y': 1.0}]}),
    ('int-from-bool', {**PAYLOAD, 'items': [{'x': True, 'y': 1.0}]}),
    ('int-garbage', {**PAYLOAD, 'items': [{'x': 'nope', 'y': 1.0}]}),
    ('float-from-str', {**PAYLOAD, 'items': [{'x': 1, 'y': '2.5'}]}),
    ('float-garbage', {**PAYLOAD, 'items': [{'x': 1, 'y': 'nope'}]}),
    ('str-wrong-type', {**PAYLOAD, 'name': 42}),
    ('bool-from-str', {**PAYLOAD, 'flag': 'yes'}),
    ('bool-garbage', {**PAYLOAD, 'flag': []}),
    ('many-not-a-list', {**PAYLOAD, 'tags': 'alpha'}),
    ('nested-not-a-dict', {**PAYLOAD, 'items': [7]}),
    ('null-value', {**PAYLOAD, 'name': None}),
    ('unknown-keys', {**PAYLOAD, 'surprise': 1}),
    ('defaults-omitted', {'name': 'd', 'items': []}),
    ('top-level-not-a-dict', ['not', 'a', 'dict']),
]


def _outcome(fn, arg):
    """``('ok', value)`` or ``('raised', ExcType, message)`` — comparable."""
    try:
        return ('ok', fn(arg))
    except Exception as exc:  # noqa: BLE001 — comparing failures is the point
        return ('raised', type(exc).__name__, str(exc))


class TestDifferential:
    @pytest.fixture
    def pair(self, use_backend):
        """The same schema built twice: accelerated, and pure Python."""
        use_backend('refcore')
        _i, accelerated = _tier1()
        _i, pure = _tier1(accel=False)
        assert accelerated.__seared_accel__.accelerated is True
        assert pure.__seared_accel__.accelerated is False
        return accelerated, pure

    @pytest.mark.parametrize(('label', 'payload'), CASES, ids=[c[0] for c in CASES])
    def test_load_matches(self, pair, label, payload):
        accelerated, pure = pair
        got = _outcome(accelerated.load, payload)
        want = _outcome(pure.load, payload)
        if want[0] == 'raised':
            assert got == want
        else:
            # Compare through dump: instances are of two distinct classes.
            assert got[0] == 'ok'
            assert accelerated.dump(got[1]) == pure.dump(want[1])

    @pytest.mark.parametrize(('label', 'payload'), CASES, ids=[c[0] for c in CASES])
    def test_dump_matches(self, pair, label, payload):
        accelerated, pure = pair
        try:
            a_obj, p_obj = accelerated.load(payload), pure.load(payload)
        except Exception:  # noqa: BLE001 — load parity is the other test's job
            pytest.skip('payload does not load')
        assert _outcome(accelerated.dump, a_obj) == _outcome(pure.dump, p_obj)

    def test_attribute_values_match(self, pair):
        accelerated, pure = pair
        a, p = accelerated.load(PAYLOAD), pure.load(PAYLOAD)
        assert a.name == p.name
        assert a.flag == p.flag
        assert a.tags == p.tags
        assert [(i.x, i.y, i.label) for i in a.items] == [(i.x, i.y, i.label) for i in p.items]

    def test_mutable_default_isolation(self, use_backend):
        use_backend('refcore')
        _inner, outer = _tier1()
        a, b = outer.load({'name': 'a', 'items': []}), outer.load({'name': 'b', 'items': []})
        a.tags.append('x')
        assert b.tags == []

    def test_lax_mode_matches(self, use_backend):
        use_backend('refcore')
        _i, accelerated = _tier1(validate=False)
        _i, pure = _tier1(validate=False, accel=False)
        lax_cases = [
            {**PAYLOAD, 'name': 42},
            {**PAYLOAD, 'flag': 'nonsense'},
            {**PAYLOAD, 'items': [{'x': True, 'y': 1}]},
        ]
        for payload in lax_cases:
            assert _outcome(accelerated.load, payload)[0] == _outcome(pure.load, payload)[0]
            assert accelerated.dump(accelerated.load(payload)) == pure.dump(pure.load(payload))

    def test_dump_skips_none_and_dump_false(self, use_backend):
        use_backend('refcore')

        @s.seared
        class Partial(s.Seared):
            shown: str | None = s.Str(default=None)
            hidden: str | None = s.Str(dump=False)

        assert Partial.__seared_accel__.accelerated is True
        assert Partial.dump(Partial.load({'shown': 'a', 'hidden': 'b'})) == {'shown': 'a'}
        assert Partial.dump(Partial.load({})) == {}

    def test_keyed_round_trip(self, use_backend):
        use_backend('refcore')

        @s.seared
        class Keyed(s.Seared):
            counts: dict[str, int] = s.Int(keyed=True, required=True)

        assert Keyed.__seared_accel__.accelerated is True
        assert Keyed.dump(Keyed.load({'counts': {'a': 1}})) == {'counts': {'a': 1}}
        with pytest.raises(s.ValidationError, match='expected dict for keyed field'):
            Keyed.load({'counts': [1]})
