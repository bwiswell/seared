from __future__ import annotations

import re

import seared as s
from seared.doc import generate
from seared.doc.generate import build_docs, check_docs, collect, main, undocumented, write_docs

TARGET = 'doc.sample'


class TestBuildDocs:
    def setup_method(self):
        self.docs = build_docs(TARGET)

    def test_paths_mirror_package_tree(self):
        assert set(self.docs) == {
            'Geo.md',
            'Widget.md',
            'telemetry/Reading.md',
            'index.md',
        }

    def test_private_base_excluded_but_fields_inherited(self):
        # `_Named` is a private base: no page of its own...
        assert '_Named.md' not in self.docs
        # ...but its `name` field is flattened onto the concrete `Widget`.
        assert '`name`' in self.docs['Widget.md']

    def test_cross_link_is_relative(self):
        # Reading (telemetry/) links up to Geo at the doc-set root.
        assert '[`Geo`](../Geo.md)' in self.docs['telemetry/Reading.md']

    def test_index_groups_by_category(self):
        index = self.docs['index.md']
        assert '## telemetry' in index
        assert '## (root)' in index
        assert '[Reading](telemetry/Reading.md)' in index
        assert '[Geo](Geo.md)' in index


class TestCollect:
    def test_closure_includes_referenced_class(self):
        # Geo is only reachable via Reading's T(Geo) — closure must pull it in.
        names = {c.__name__ for c in collect('doc.sample.telemetry.reading')}
        assert {'Reading', 'Geo'} <= names


class TestEveryLinkHasAPage:
    """Every class a page links to is collected, so no link dangles (0.4.1)."""

    def test_a_bare_class_and_a_fieldless_variant_are_collected(self):
        names = {c.__name__ for c in collect('doc.linked')}
        assert names == {'Bare', 'Command', 'Go', 'Stop'}

    def test_no_page_links_to_a_page_that_isnt_there(self):
        docs = build_docs('doc.linked')
        targets = set(re.findall(r'\]\(([^)#]+\.md)\)', docs['Command.md']))
        assert targets == {'Bare.md', 'Go.md', 'Stop.md'}
        assert targets <= set(docs)


class TestWriteAndCheck:
    def test_write_then_check_in_sync(self, tmp_path):
        docs = build_docs(TARGET)
        written, unchanged = write_docs(docs, str(tmp_path))
        assert written == len(docs)
        assert unchanged == 0
        assert check_docs(docs, str(tmp_path)) == []

    def test_check_detects_missing(self, tmp_path):
        docs = build_docs(TARGET)
        # nothing written yet -> everything missing
        drift = check_docs(docs, str(tmp_path))
        assert len(drift) == len(docs)
        assert all(d.startswith('missing:') for d in drift)

    def test_check_detects_stale(self, tmp_path):
        docs = build_docs(TARGET)
        write_docs(docs, str(tmp_path))
        (tmp_path / 'Geo.md').write_text('tampered', encoding='utf-8')
        drift = check_docs(docs, str(tmp_path))
        assert drift == ['stale:   Geo.md']

    def test_write_is_idempotent(self, tmp_path):
        docs = build_docs(TARGET)
        write_docs(docs, str(tmp_path))
        written, unchanged = write_docs(docs, str(tmp_path))
        assert written == 0
        assert unchanged == len(docs)

    def test_write_leaves_foreign_files(self, tmp_path):
        docs = build_docs(TARGET)
        write_docs(docs, str(tmp_path))
        sentinel = tmp_path / 'KEEP.txt'
        sentinel.write_text('keep', encoding='utf-8')
        write_docs(docs, str(tmp_path))
        assert sentinel.read_text(encoding='utf-8') == 'keep'


class TestUndocumented:
    def test_each_field_without_a_doc_in_collects_order(self):
        # Widget's ``name`` comes from its private base, and is reported on the page that shows it.
        assert undocumented(TARGET) == [
            'doc.sample.shared.Geo.lon',
            'doc.sample.shared.Widget.name',
            'doc.sample.shared.Widget.size',
            'doc.sample.telemetry.reading.Reading.source',
            'doc.sample.telemetry.reading.Reading.value',
            'doc.sample.telemetry.reading.Reading.where',
        ]

    def test_a_fully_documented_set_has_none(self):
        assert undocumented('doc.documented') == []

    def test_a_doc_of_only_whitespace_counts_as_missing(self, monkeypatch):
        @s.seared
        class Blank(s.Seared):
            n: int = s.Int(default=0, doc='   ')

        monkeypatch.setattr(generate, 'collect', lambda _target: [Blank])
        assert undocumented('anything') == [f'{__name__}.{Blank.__qualname__}.n']


class TestRequireDocs:
    def test_a_missing_doc_fails_before_anything_is_written(self, tmp_path, capsys):
        assert main([TARGET, '-o', str(tmp_path), '--require-docs']) == 1
        assert list(tmp_path.iterdir()) == []
        err = capsys.readouterr().err
        assert "6 field(s) without doc= under 'doc.sample':" in err
        assert '  doc.sample.shared.Geo.lon\n' in err

    def test_it_fails_before_a_check_too(self, tmp_path, capsys):
        assert main([TARGET, '-o', str(tmp_path), '--check', '--require-docs']) == 1
        assert 'without doc=' in capsys.readouterr().err

    def test_with_every_field_documented_it_generates_as_usual(self, tmp_path):
        assert main(['doc.documented', '-o', str(tmp_path), '--require-docs']) == 0
        assert (tmp_path / 'index.md').exists()

    def test_without_the_flag_a_missing_doc_is_fine(self, tmp_path):
        assert main([TARGET, '-o', str(tmp_path)]) == 0
