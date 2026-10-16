"""Pure-Python reference accelerator backend.

Implements the backend protocol from ``seared._core.accel`` — ``SPEC_ABI``,
``compile_spec(spec) -> (load, dump)`` — so the seam can be exercised end to
end with no compiled core installed. `rusted` is the real implementation of
this same contract.

Three properties make it a useful oracle rather than a mock:

- **It interprets the spec, not the ``Field`` objects.** Coercion is
  reimplemented here from the ``kind`` string alone. Anything the spec fails
  to carry shows up as a test failure here, which is the whole point of
  standing this up before writing Rust.
- **It constructs via ``__new__`` + attribute assignment**, bypassing
  ``__init__`` exactly as a compiled core must. So the differential suite
  measures the construction-path divergence too, not just coercion.
- **It imports nothing from seared**, the exception class included — that
  rides in the spec. A compiled backend ships as an independent wheel and
  *cannot* import the library it accelerates, so an oracle that could would
  hide exactly the gap this is meant to surface.

Scope is deliberately **Tier 1 only** (`int` / `float` / `str` / `bool` /
`T`). It exists to prove the seam works with no compiled core present — on a
platform with no wheel, or in CI with no Rust toolchain — not to be a second
full implementation. It declines everything else, which is a legal backend
answer and exercises the decline path for free.

Not shipped: ``tests/`` is on ``pythonpath``, so seared's own suite can run
against it with ``SEARED_ACCEL=require SEARED_ACCEL_BACKEND=refcore``.
"""

from __future__ import annotations

from typing import Any

SPEC_ABI = 2
SUPPORTS_SEARED = '>=0.4,<0.5'
__version__ = '0.0.0'


# ---------------------------------------------------------------------------
# Scalar coercion — mirrors seared/fields/{int_,float_,str_,bool_}.py exactly.
# ``err`` is the exception class carried in the spec.
# ---------------------------------------------------------------------------


def _de_int(v, validate, err):
    if isinstance(v, bool):
        if validate:
            msg = 'expected int, got bool'
            raise err(msg)
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, (str, float)):
        try:
            return int(v)
        except (TypeError, ValueError) as e:
            msg = f'cannot deserialize {v!r} as int'
            raise err(msg) from e
    msg = f'cannot deserialize {v!r} as int'
    raise err(msg)


def _ser_int(v, validate, err):
    if validate and (isinstance(v, bool) or not isinstance(v, int)):
        msg = f'expected int, got {type(v).__name__}'
        raise err(msg)
    return int(v)


def _de_float(v, validate, err):
    if isinstance(v, bool):
        if validate:
            msg = 'expected float, got bool'
            raise err(msg)
        return float(v)
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError as e:
            msg = f'cannot deserialize {v!r} as float'
            raise err(msg) from e
    msg = f'cannot deserialize {v!r} as float'
    raise err(msg)


def _ser_float(v, validate, err):
    if validate and (isinstance(v, bool) or not isinstance(v, (int, float))):
        msg = f'expected float, got {type(v).__name__}'
        raise err(msg)
    return float(v)


def _de_str(v, validate, err):
    if isinstance(v, str):
        return v
    if validate:
        msg = f'expected str, got {type(v).__name__}'
        raise err(msg)
    return str(v)


def _ser_str(v, validate, err):
    if validate and not isinstance(v, str):
        msg = f'expected str, got {type(v).__name__}'
        raise err(msg)
    return str(v)


_TRUE = ('true', '1', 'yes', 'on')
_FALSE = ('false', '0', 'no', 'off')


def _de_bool(v, validate, err):
    # ``fields/bool_.py``: both modes read the spelling table first, and only
    # then does lax fall back to truthiness (``'maybe'`` is ``True``). The
    # SPEC_ABI 1 answer skipped the table in lax mode, so ``'false'`` was
    # ``True``; seared declined lax ``Bool`` until ABI 2 carried the fix.
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        low = v.strip().lower()
        if low in _TRUE:
            return True
        if low in _FALSE:
            return False
    if not validate:
        return bool(v)
    if isinstance(v, int):
        return bool(v)
    msg = f'cannot deserialize {v!r} as bool'
    raise err(msg)


def _ser_bool(v, validate, err):
    if validate and not isinstance(v, bool):
        msg = f'expected bool, got {type(v).__name__}'
        raise err(msg)
    return bool(v)


_SCALARS = {
    'int': (_de_int, _ser_int),
    'float': (_de_float, _ser_float),
    'str': (_de_str, _ser_str),
    'bool': (_de_bool, _ser_bool),
}


# ---------------------------------------------------------------------------
# Compilation
# ---------------------------------------------------------------------------


def _prepare(fspec: dict[str, Any], validate: bool, err) -> dict[str, Any]:
    """Bind one field spec to its coercion pair."""
    kind = fspec['kind']
    if kind == 'nested':
        sub = fspec['schema']
        sub_load, sub_dump = compile_spec(sub)
        sub_cls = sub['cls']

        def de_one(v, _validate, format):
            # T.deserialize: an already-built instance passes through, and the
            # nested load runs under the nested class's own validate flag.
            if isinstance(v, sub_cls):
                return v
            return sub_load(v, format)

        def ser_one(v, validate_, format):
            # The guard uses the *parent's* flag; the dump uses the nested one.
            if not isinstance(v, sub_cls) and validate_:
                msg = f'expected {sub["name"]}, got {type(v).__name__}'
                raise err(msg)
            return sub_dump(v, format)
    else:
        de_scalar, ser_scalar = _SCALARS[kind]

        def de_one(v, validate_, format, _f=de_scalar):
            return _f(v, validate_, err)

        def ser_one(v, validate_, format, _f=ser_scalar):
            return _f(v, validate_, err)

    return {**fspec, 'de_one': de_one, 'ser_one': ser_one, 'validate': validate}


def _relocated(e, err, *segments, cls_name=None):
    """``e`` rebuilt with ``segments`` prepended to its path, and ``cls_name`` set.

    The ABI 2 error contract: a backend raises ``err(reason, path=…,
    cls_name=…)`` and must end with the same three parts, and so the same
    message, as the Python path. It may build them any way it likes. This
    oracle rebuilds through the public constructor at each level, as a
    compiled core would; seared's own path mutates in place instead.
    """
    return err(e.reason, path=(*segments, *e.path), cls_name=e.cls_name if cls_name is None else cls_name)


def _apply(f, v, one, validate, format, err):
    """Mirrors ``seared._core.decorator._apply`` — keyed / many orchestration; ``v`` is never ``None``."""
    if f['keyed']:
        if validate and not isinstance(v, dict):
            msg = f'expected dict for keyed field, got {type(v).__name__}'
            raise err(msg)
        out = {}
        for k, x in v.items():
            try:
                out[k] = one(x, validate, format)
            except err as e:
                raise _relocated(e, err, k) from None
        return out
    if f['many']:
        if validate and not isinstance(v, (list, tuple)):
            msg = f'expected list for many field, got {type(v).__name__}'
            raise err(msg)
        items = []
        for i, x in enumerate(v):
            try:
                items.append(one(x, validate, format))
            except err as e:
                raise _relocated(e, err, i) from None
        return items
    return one(v, validate, format)


def _load_value(f, data, name, validate, format, err):
    """One field's value on load — mirrors the decorator's resolution order."""
    wire = f['wire']
    v = data.get(wire)
    if v is not None:
        try:
            return _apply(f, v, f['de_one'], validate, format, err)
        except err as e:
            raise _relocated(e, err, wire, cls_name=name) from None
    # A ``null`` is a value only on a nullable field; elsewhere it reads as absent.
    if f['nullable'] and wire in data:
        return None
    if f['required']:
        msg = 'required key missing'
        raise err(msg, path=(wire,), cls_name=name)
    if f['default_factory'] is not None:
        return f['default_factory']()
    return f['default']


def _dump_into(out, f, v, name, validate, format, err):
    """One field's wire value on dump; a failure's path names the attribute.

    ``None`` is written as ``null`` only on a nullable field, and left out
    everywhere else.
    """
    if v is None:
        if f['nullable']:
            out[f['wire']] = None
        return
    try:
        out[f['wire']] = _apply(f, v, f['ser_one'], validate, format, err)
    except err as e:
        raise _relocated(e, err, f['attr'], cls_name=name) from None


def compile_spec(spec: dict[str, Any]) -> tuple[Any, Any] | None:
    """Build ``(load, dump)`` callables for one class spec.

    Returns:
        A ``(load, dump)`` pair with the same signatures as the decorator's
        own closures — ``load(data, format)`` and ``dump(obj, format)`` — or
        ``None`` to decline a kind this backend doesn't implement.
    """
    if spec['abi'] != SPEC_ABI:
        msg = f'refcore understands SPEC_ABI {SPEC_ABI}, got {spec["abi"]!r}'
        raise ValueError(msg)

    cls = spec['cls']
    name = spec['name']
    validate = spec['validate']
    err = spec['error']
    if any(f['kind'] != 'nested' and f['kind'] not in _SCALARS for f in spec['fields']):
        return None
    fields = [_prepare(f, validate, err) for f in spec['fields']]

    def load(data, format='json'):
        if not isinstance(data, dict):
            msg = f'expected dict, got {type(data).__name__}'
            raise err(msg, cls_name=name)
        # ``__new__`` + setattr, bypassing __init__ — the construction path a
        # compiled core uses. The accel seam declines any class where that is
        # observable (custom __init__ / __post_init__).
        obj = cls.__new__(cls)
        for f in fields:
            object.__setattr__(obj, f['attr'], _load_value(f, data, name, validate, format, err))
        return obj

    def dump(obj, format='json'):
        out = {}
        for f in fields:
            if f['dump']:
                _dump_into(out, f, getattr(obj, f['attr'], None), name, validate, format, err)
        return out

    return load, dump
