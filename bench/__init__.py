"""Performance bench for seared — ships with the repo, not the package.

Compares seared (strict + lax) against marshmallow and pydantic on a
representative nested schema, and records the results as a committed JSON
artifact (``bench/results.json``).

Comparator libraries are NOT seared dependencies; they live behind the
``bench`` extra. From the repo root:

    uv sync --extra bench
    uv run python -m bench

Methodology and recorded results: ``docs/overview/benchmarks.md``.
"""
