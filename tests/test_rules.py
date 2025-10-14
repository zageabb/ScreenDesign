import pytest
from rules import eval_expr, apply_rules

def test_eval_basic():
    assert eval_expr('1 + 2 * 3', {}) == 7
    assert eval_expr('len("abc")', {}) == 3

def test_apply_rules():
    rules = {"show": [{"when": "mileage > 0", "targets": ["notes"]}]}
    r = apply_rules(rules, {"mileage": 10})
    assert "notes" in r["show"]
