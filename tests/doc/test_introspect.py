from __future__ import annotations

from doc.models import Band, Demo, Inner, StartCmd

from seared.doc import introspect, is_seared_class


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
        assert _field(self.schema, 'note').default_repr == '`null`'

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


class TestIsSearedClass:
    def test_recognises_models(self):
        assert is_seared_class(Demo)
        assert is_seared_class(Inner)

    def test_rejects_non_models(self):
        assert not is_seared_class(Band)
        assert not is_seared_class(int)
        assert not is_seared_class(is_seared_class)
