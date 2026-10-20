from __future__ import annotations

import typing

import seared as s
from doc.models import Band, Demo, Inner, StartCmd
from seared.doc import FieldDoc, document, introspect, is_seared_class


def _field(schema, attr):
    return next(f for f in schema.fields if f.attr == attr)


class TestIntrospect:
    def setup_method(self):
        self.schema = introspect(Demo)

    def test_class_metadata(self):
        assert self.schema.name == 'Demo'
        assert self.schema.summary == 'A demo model.'
        assert 'Second paragraph.' in self.schema.doc

    def test_types_resolved(self):
        assert _field(self.schema, 'source').type_str == 'str'
        assert _field(self.schema, 'tags').type_str == 'list[int]'
        assert _field(self.schema, 'ratios').type_str == 'dict[str, float]'
        assert _field(self.schema, 'note').type_str == 'str | None'

    def test_required_and_defaults(self):
        assert _field(self.schema, 'source').required is True
        assert _field(self.schema, 'source').default_repr == '—'
        assert _field(self.schema, 'tags').default_repr == '`<factory: list>`'
        assert _field(self.schema, 'band').default_repr == '`Band.UHF`'
        # The attribute's value, ``None``; not ``null``, which a field that
        # isn't nullable never loads or dumps.
        assert _field(self.schema, 'note').default_repr == '`None`'

    def test_doc_and_wire_key(self):
        assert _field(self.schema, 'source').doc == 'origin | system'
        assert _field(self.schema, 'note').wire_key == 'n'
        assert _field(self.schema, 'source').wire_key is None

    def test_dump_false(self):
        assert _field(self.schema, 'hidden').dump is False

    def test_enum(self):
        e = _field(self.schema, 'band').enum
        assert e.name == 'Band'
        assert e.members == (('UHF', 0), ('HF', 1))

    def test_nested_and_references(self):
        assert _field(self.schema, 'inner').nested is Inner
        assert Inner in self.schema.references
        assert StartCmd in self.schema.references

    def test_variants(self):
        f = _field(self.schema, 'action')
        assert f.envelope == 'flat'
        assert [(v.tag, v.cls) for v in f.variants] == [('start', StartCmd)]

    def test_a_union_is_required_with_no_default(self):
        # Its tag is required on the wire whatever ``required`` says, and it
        # takes no default.
        f = _field(self.schema, 'action')
        assert (f.required, f.default_repr) == (True, '—')

    def test_nullable(self):
        reading, fix = _field(self.schema, 'reading'), _field(self.schema, 'fix')
        assert (reading.nullable, reading.required, reading.default_repr) == (True, False, '`None`')
        assert (fix.nullable, fix.required, fix.default_repr) == (True, True, '—')
        assert _field(self.schema, 'note').nullable is False

    def test_field_doc_still_constructs_positionally(self):
        # ``nullable`` was appended with a default, so a renderer building
        # ``FieldDoc``s itself keeps working.
        fd = FieldDoc('a', None, 'int', False, '`None`', False, False, True, None)  # noqa: FBT003 — positional is the point
        assert fd.nullable is False


class TestDocstringCleanup:
    def test_rst_roles_stripped(self):
        import seared as s

        @s.seared
        class R(s.Seared):
            """:class:`Foo` builds a :meth:`bar` thing."""

            a: int = s.Int(default=0)

        schema = introspect(R)
        assert schema.summary == '`Foo` builds a `bar` thing.'
        assert ':class:' not in schema.doc
        assert ':meth:' not in schema.doc


class TestDtype:
    def test_an_ndarrays_dtype_reaches_the_model_and_the_notes(self):
        @s.seared
        class Samples(s.Seared):
            values: object = s.NDArray(dtype='float32', required=True, doc='the samples')
            loose: object = s.NDArray(default=None)

        fields = {f.attr: f for f in introspect(Samples).fields}
        assert (fields['values'].dtype, fields['loose'].dtype) == ('float32', None)
        assert 'the samples · dtype: `float32`' in document(Samples)


class TestKind:
    def test_each_field_carries_its_kind_a_subclass_its_bases(self):
        class Trimmed(s.Str):
            pass

        @s.seared
        class Kinds(s.Seared):
            n: int = s.Int(default=0)
            name: str = Trimmed(default='')
            inner: Inner | None = s.T(Inner, default=None)
            pair: tuple = s.Tuple(s.Int(), s.Str(), default=(0, ''))

        fields = {f.attr: f.kind for f in introspect(Kinds).fields}
        assert fields == {
            'n': s.FieldKind.INT,
            'name': s.FieldKind.STR,
            'inner': s.FieldKind.NESTED,
            'pair': s.FieldKind.TUPLE,
        }


class TestConstraints:
    def test_each_fields_bounds_reach_the_model_and_the_notes(self):
        # 0.4.4: as ``(option, value)`` pairs, in a fixed order whatever the declaration's.
        @s.seared
        class Limits(s.Seared):
            count: int = s.Int(lt=10, ge=0, default=0, doc='how many')
            share: float = s.Float(gt=0, default=1.0)
            free: int = s.Int(default=0)

        fields = {f.attr: f.constraints for f in introspect(Limits).fields}
        assert fields == {'count': (('ge', 0), ('lt', 10)), 'share': (('gt', 0),), 'free': ()}
        page = document(Limits)
        assert 'how many · bounds: `>= 0`, `< 10` |' in page
        assert '| bounds: `> 0` |' in page


class TestTypeStrings:
    def test_annotations_resolve_rather_than_falling_back_to_their_text(self):
        # 0.4.3: in 0.4.1 and 0.4.2 `get_type_hints` failed on every seared class,
        # so the type column showed raw annotation text: `typing.Optional[int]`.
        # (`typing` is imported at module level: the annotations are evaluated there.)
        @s.seared
        class Legacy(s.Seared):
            n: typing.Optional[int] = s.Int(default=None)  # noqa: UP045 — the old spelling, on purpose
            tags: typing.List[str] = s.Str(many=True, default_factory=list)  # noqa: UP006 — likewise

        fields = {f.attr: f.type_str for f in introspect(Legacy).fields}
        assert fields == {'n': 'int | None', 'tags': 'list[str]'}


class TestUndocumentedClass:
    def test_has_no_summary_rather_than_the_dataclass_signature(self):
        # Before 0.4.1 the page's summary was the signature ``dataclass()`` writes into ``__doc__``.
        @s.seared
        class NoDoc(s.Seared):
            n: int = s.Int(default=0)

        schema = introspect(NoDoc)
        assert (schema.summary, schema.doc) == (None, None)
        assert 'Int(' not in document(NoDoc)


class TestIsSearedClass:
    def test_recognises_models(self):
        assert is_seared_class(Demo)
        assert is_seared_class(Inner)

    def test_rejects_non_models(self):
        assert not is_seared_class(Band)
        assert not is_seared_class(int)
        assert not is_seared_class(is_seared_class)

    def test_a_decorated_class_without_the_base_counts(self):
        # ``@zeared`` is the same decorator, and neither needs the base class (0.4.1).
        @s.seared
        class Bare:
            n: int = s.Int(default=0)

        assert is_seared_class(Bare)

    def test_a_decorated_class_without_fields_counts(self):
        @s.seared
        class Empty(s.Seared):
            pass

        assert is_seared_class(Empty)

    def test_only_what_the_decorator_built_counts(self):
        class Undecorated(s.Seared):
            pass

        class Inherited(Inner):  # a decorated parent; never decorated itself
            pass

        assert not is_seared_class(s.Seared)
        assert not is_seared_class(Undecorated)
        assert not is_seared_class(Inherited)


class TestUnionFallback:
    """Pin: a ``Union``'s fallback variant is read from ``fallback=`` (its name since 0.4.0) and rendered."""

    def test_the_fallback_reaches_the_doc_model_and_the_page(self):
        @s.seared
        class Catchall(s.Seared):
            raw: str | None = s.Str(default=None)

        @s.seared
        class Cmd(s.Seared):
            action: object = s.Union(variants={'start': StartCmd}, fallback=Catchall)

        assert _field(introspect(Cmd), 'action').fallback is Catchall
        assert 'Unknown tags fall back to `Catchall`.' in document(Cmd)
