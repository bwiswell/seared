from __future__ import annotations

from seared.doc.generate import build_docs, check_docs, collect, write_docs

TARGET = 'doc.sample'


class TestBuildDocs:
    def setup_method(self):
        self.docs = build_docs(TARGET)

    def test_paths_mirror_package_tree(self):
        assert set(self.docs) == {
            'Geo.md', 'Widget.md', 'telemetry/Reading.md', 'index.md',
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
