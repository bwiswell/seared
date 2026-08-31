"""Type-checker regression tests: run ``ty`` over the fixtures in this dir.

``ok_idiom.py`` must type-clean; ``must_error.py`` must be flagged with the
expected diagnostics. Skipped when ``ty`` isn't on PATH (e.g. a minimal env).
These are the guardrail for the PEP 681 ``@dataclass_transform`` support — see
``project-plans/01-ty-compat-dataclass-transform.md``.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
TY = shutil.which('ty')
pytestmark = pytest.mark.skipif(TY is None, reason='ty not installed')


def _run_ty(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [TY, 'check', '--python-version', '3.14', str(HERE / fixture)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_ok_idiom_typechecks() -> None:
    result = _run_ty('ok_idiom.py')
    assert result.returncode == 0, f'expected clean, got:\n{result.stdout}\n{result.stderr}'


@pytest.mark.parametrize(
    'diagnostic',
    ['missing-argument', 'unknown-argument', 'unresolved-attribute'],
)
def test_must_error_is_flagged(diagnostic: str) -> None:
    result = _run_ty('must_error.py')
    assert result.returncode != 0, 'expected ty to report errors, but it passed'
    assert diagnostic in result.stdout, f'expected {diagnostic!r} in ty output:\n{result.stdout}'
