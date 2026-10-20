"""Tests for ``seared.fields.constraints``: what a field declares, and the declarations it refuses (0.4.4).

A pattern's tests hold seared to ECMA-262, the regex dialect JSON Schema reads, through
``ecma_verdicts.json``: verdicts recorded from Node (``new RegExp(pattern, 'u')``), since
``jsonschema`` evaluates ``pattern`` with Python's ``re`` and can't show where the two differ.
"""

from __future__ import annotations

import json
import math
import pathlib
import re

import pytest

import seared as s
from seared.fields.constraints import check_bounds, declared_constraints, number_bounds, portable_regex, string_checks

VERDICTS = json.loads(pathlib.Path(__file__).with_name('ecma_verdicts.json').read_text(encoding='utf-8'))


class TestDeclaredConstraints:
    def test_none_on_an_unbounded_field(self):
        assert declared_constraints(s.Int()) == {}

    def test_the_options_set_in_a_fixed_order(self):
        assert declared_constraints(s.Float(lt=1.0, ge=0)) == {'ge': 0, 'lt': 1.0}

    def test_a_strs_lengths(self):
        assert declared_constraints(s.Str(max_length=4, min_length=1)) == {'min_length': 1, 'max_length': 4}

    def test_a_strs_pattern_comes_last(self):
        assert declared_constraints(s.Str(pattern='^a', min_length=1)) == {'min_length': 1, 'pattern': '^a'}

    @pytest.mark.parametrize('field', [s.Str(), s.Bool(), s.Path(), s.T(s.Seared), object()])
    def test_none_on_anything_without_the_options(self, field):
        assert declared_constraints(field) == {}


class TestNumberBounds:
    def test_none_when_none_are_declared(self):
        assert number_bounds(s.Int(), integral=True) is None

    def test_the_lower_bound_first(self):
        bounds = number_bounds(s.Int(le=9, gt=0), integral=True)
        assert [(symbol, bound) for _, symbol, bound in bounds] == [('>', 0), ('<=', 9)]

    @pytest.mark.parametrize(('low', 'high'), [('ge', 'le'), ('ge', 'lt'), ('gt', 'le'), ('gt', 'lt')])
    def test_a_range_with_room_is_accepted(self, low, high):
        s.Int(**{low: 1, high: 3})

    def test_a_range_of_one_value_is_accepted(self):
        s.Int(ge=1, le=1)


class TestRefusedDeclarations:
    """Each raises ``TypeError`` where the field is declared."""

    @pytest.mark.parametrize(
        ('field', 'options', 'message'),
        [
            (s.Int, {'ge': 0.5}, 'Int: ge= takes an int, got 0.5'),
            (s.Int, {'lt': True}, 'Int: lt= takes an int, got True'),
            (s.Int, {'le': '9'}, "Int: le= takes an int, got '9'"),
            (s.Float, {'gt': False}, 'Float: gt= takes a number, got False'),
            (s.Float, {'ge': '0'}, "Float: ge= takes a number, got '0'"),
            (s.Float, {'ge': math.nan}, 'Float: ge= takes a finite number, got nan'),
            (s.Float, {'le': math.inf}, 'Float: le= takes a finite number, got inf'),
        ],
    )
    def test_a_bound_of_the_wrong_type(self, field, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            field(**options)

    @pytest.mark.parametrize(
        ('options', 'message'),
        [
            ({'ge': 0, 'gt': 0}, 'Int: ge= and gt= both set a lower bound; keep one'),
            ({'le': 9, 'lt': 9}, 'Int: le= and lt= both set an upper bound; keep one'),
        ],
    )
    def test_two_bounds_on_one_side(self, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            s.Int(**options)

    @pytest.mark.parametrize(
        ('options', 'message'),
        [
            ({'ge': 5, 'le': 1}, 'Int: ge=5 and le=1 leave no value'),
            ({'ge': 1, 'lt': 1}, 'Int: ge=1 and lt=1 leave no value'),
            ({'gt': 1, 'le': 1}, 'Int: gt=1 and le=1 leave no value'),
        ],
    )
    def test_an_empty_range(self, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            s.Int(**options)

    def test_a_float_range_with_an_int_bound(self):
        with pytest.raises(TypeError, match=r'^Float: gt=1 and lt=0\.5 leave no value$'):
            s.Float(gt=1, lt=0.5)


class TestStringChecks:
    def test_none_when_none_are_declared(self):
        assert string_checks(s.Str()) is None

    @pytest.mark.parametrize(
        ('options', 'message'),
        [
            ({'min_length': -1}, 'Str: min_length= takes a non-negative int, got -1'),
            ({'max_length': 1.5}, 'Str: max_length= takes a non-negative int, got 1.5'),
            ({'min_length': True}, 'Str: min_length= takes a non-negative int, got True'),
            ({'max_length': '4'}, "Str: max_length= takes a non-negative int, got '4'"),
            ({'min_length': 5, 'max_length': 3}, 'Str: min_length=5 and max_length=3 leave no value'),
        ],
    )
    def test_a_declaration_that_cant_hold(self, options, message):
        with pytest.raises(TypeError, match=f'^{re.escape(message)}$'):
            s.Str(**options)

    @pytest.mark.parametrize('options', [{'min_length': 4, 'max_length': 4}, {'max_length': 0}, {'min_length': 0}])
    def test_a_range_with_one_length_is_accepted(self, options):
        s.Str(**options)


def _passes(field, text):
    try:
        field.deserialize(text)
    except s.ValidationError:
        return False
    return True


class TestPortablePatterns:
    """Pin: within the subset, seared matches as ECMA-262 does; outside it, it refuses the pattern."""

    @pytest.mark.parametrize('case', VERDICTS['accepted'], ids=lambda case: repr(case['pattern']))
    def test_each_input_matches_as_in_ecma_262(self, case):
        assert case['ecma'] == 'compiles'
        field = s.Str(pattern=case['pattern'])
        for text, ecma in zip(case['inputs'], case['matches'], strict=True):
            assert _passes(field, text) is ecma, repr(text)

    @pytest.mark.parametrize('case', VERDICTS['refused'], ids=lambda case: repr(case['pattern']))
    def test_a_pattern_outside_the_subset_is_refused(self, case):
        # Most of these ECMA-262 rejects outright; the rest compile in both
        # engines but match differently, or make Python raise or warn.
        with pytest.raises(TypeError, match=r'^Str: pattern='):
            s.Str(pattern=case['pattern'])

    def test_the_corpus_covers_both_kinds_of_refusal(self):
        verdicts = {case['ecma'] for case in VERDICTS['refused']}
        assert verdicts == {'compiles', 'SyntaxError'}


class TestPatternRefusals:
    """Pin: a refusal names the construct, where it is, and its portable spelling where it has one."""

    @pytest.mark.parametrize(
        ('pattern', 'detail'),
        [
            (r'\d+', r"\d at 0 isn't portable; write [0-9]"),
            (r'^\w$', r"\w at 1 isn't portable; write [A-Za-z0-9_]"),
            (r'a\b', r"\b at 1 isn't portable (a word boundary)"),
            (r'(a)\1', r"\1 at 3 isn't portable (a backreference)"),
            (r'\-', r"\- at 0 isn't portable; write a plain -, which needs no escape outside a class"),
            (r'\:', r"\: at 0 isn't portable; escape only ^ $ \ . * + ? ( ) [ ] { } | /"),
            (r'[\:]', r"\: at 1 isn't portable; escape only ^ $ \ . * + ? ( ) [ ] { } | / -"),
            (r'[\b]', r"\b at 1 isn't portable; write \x08"),
            (r'\uD83D', r"\uD83D at 0 isn't portable; write the character itself, not its surrogates"),
            (r'\u{1F600}', r"\u at 0 isn't portable; write \uHHHH (four hex digits), or the character itself"),
            ('(?<=a)b', "(?<= at 0 isn't portable (lookbehind)"),
            ('(?P<n>a)', "(?P at 0 isn't portable (a named group)"),
            ('(?i)a', "(?i at 0 isn't portable (an inline flag)"),
            ('a*+', "+ at 2 isn't portable (a quantifier on a quantifier)"),
            ('^*', "* at 1 isn't portable (a repeated assertion)"),
            ('(?=a)*', "* at 5 isn't portable (a repeated assertion)"),
            ('*a', '* at 0 has nothing to repeat'),
            ('a{,3}', "{,3} at 1 isn't portable; write {0,3}"),
            ('a{3,2}', '{3,2} at 1 counts down; put the smaller number first'),
            ('a{', r"{ at 1 isn't portable; escape it as \{"),
            ('a]', r"] at 1 isn't portable; escape it as \]"),
            ('[]a]', r"] at 1 isn't portable; a class can't open with it, so escape it as \]"),
            ('[[a]', r"[ at 1 isn't portable; escape it as \[ inside a class"),
            ('[a&&b]', r"&& at 2 isn't portable; escape one of them: \&&"),
            ('[a-b-c]', r"- at 4 isn't portable; escape it as \-, or put it first or last in the class"),
            ('[--a]', r"- at 1 isn't portable; escape a range that starts or ends at - as \-"),
            ('(a', '( at 0 is never closed'),
            ('a)', ') at 1 closes no group'),
            ('[a', '[ at 0 is never closed'),
            ('a\\', r'\ at 1 escapes nothing'),
        ],
    )
    def test_the_message(self, pattern, detail):
        with pytest.raises(TypeError, match=f'^{re.escape(f"Str: pattern={pattern!r}: {detail}")}$'):
            s.Str(pattern=pattern)

    def test_one_that_doesnt_compile(self):
        with pytest.raises(TypeError, match=r"^Str: pattern='\[z-a\]' doesn't compile: bad character range"):
            s.Str(pattern='[z-a]')

    @pytest.mark.parametrize(
        ('pattern', 'got'),
        [(re.compile('a'), 'a compiled pattern, whose flags JSON Schema has no form for'), (5, '5'), (b'a', "b'a'")],
    )
    def test_only_a_str(self, pattern, got):
        with pytest.raises(TypeError, match=f'^{re.escape(f"Str: pattern= takes a str, got {got}")}$'):
            s.Str(pattern=pattern)


class TestTranslation:
    """Pin: outside a class, ``$`` and ``.`` are rewritten; everything else is kept as written."""

    @pytest.mark.parametrize(
        ('pattern', 'python'),
        [
            ('^a$', r'^a\Z'),
            ('a.c', r'a[^\n\r\u2028\u2029]c'),
            ('[.$]', '[.$]'),
            (r'^(?:a|b)+?\.\$$', r'^(?:a|b)+?\.\$\Z'),
            (r'[\-a-z\]]{2,3}', r'[\-a-z\]]{2,3}'),
        ],
    )
    def test_what_python_compiles(self, pattern, python):
        assert portable_regex(pattern).pattern == python

    def test_the_owner_names_a_subclass(self):
        with pytest.raises(TypeError, match=r'^Slug: pattern='):
            portable_regex(r'\d', 'Slug')


class TestDefaults:
    """A static ``default`` must pass the field's own bounds."""

    def test_a_default_outside_the_bounds_is_refused(self):
        with pytest.raises(TypeError, match=r'^Int: default -1 fails its constraints: must be >= 0, got -1$'):
            s.Int(ge=0, default=-1)

    def test_each_element_of_a_many_default_is_checked(self):
        with pytest.raises(TypeError, match=r'^Float: default 2\.0 fails its constraints: must be < 1\.0, got 2\.0$'):
            s.Float(lt=1.0, many=True, default=[0.5, 2.0])

    def test_each_value_of_a_keyed_default_is_checked(self):
        with pytest.raises(TypeError, match=r'^Int: default 11 fails its constraints'):
            s.Int(le=10, keyed=True, default={'a': 1, 'b': 11})

    def test_a_default_inside_the_bounds_is_accepted(self):
        assert s.Int(ge=0, default=0).default == 0

    def test_a_default_factory_is_not_called(self):
        calls = []
        s.Int(ge=0, default_factory=lambda: calls.append(1))
        assert calls == []

    def test_a_strs_default_must_pass_its_lengths(self):
        with pytest.raises(TypeError, match=r"^Str: default 'ab' fails its constraints: must be at least 3 characters"):
            s.Str(min_length=3, default='ab')

    def test_each_element_of_a_strs_many_default_is_checked(self):
        with pytest.raises(TypeError, match=r"^Str: default '' fails its constraints"):
            s.Str(min_length=1, many=True, default=['ok', ''])

    def test_a_strs_default_must_match_its_pattern(self):
        with pytest.raises(
            TypeError, match=r"^Str: default 'A' fails its constraints: must match the pattern '\^\[a-z\]\+\$'$"
        ):
            s.Str(pattern='^[a-z]+$', default='A')


class TestCheckBounds:
    BOUNDS = number_bounds(s.Float(ge=0, le=1), integral=False)

    @pytest.mark.parametrize('value', [0, 0.5, 1])
    def test_a_value_within_passes(self, value):
        check_bounds(value, self.BOUNDS)

    def test_nan_fails_every_bound(self):
        with pytest.raises(s.ValidationError, match=r'^must be >= 0, got nan$'):
            check_bounds(math.nan, self.BOUNDS)
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got nan$'):
            check_bounds(math.nan, number_bounds(s.Float(le=1), integral=False))

    def test_an_infinity_passes_a_lower_bound_and_fails_an_upper_one(self):
        check_bounds(math.inf, number_bounds(s.Float(ge=0), integral=False))
        with pytest.raises(s.ValidationError, match=r'^must be <= 1, got inf$'):
            check_bounds(math.inf, self.BOUNDS)
