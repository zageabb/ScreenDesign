from __future__ import annotations
import ast
from typing import Any, Dict

_ALLOWED_FUNCS = {
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
}

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Call, ast.Load, ast.Name, ast.Constant, ast.Subscript, ast.Index,
    ast.Attribute, ast.Dict, ast.List, ast.Tuple,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot
)

def _safe(node: ast.AST) -> None:
    for child in ast.walk(node):
        if not isinstance(child, _ALLOWED_NODES):
            raise ValueError(f"Disallowed expression: {type(child).__name__}")

def eval_expr(expr: str, ctx: Dict[str, Any]) -> Any:
    """Evaluate a small expression safely against ctx."""
    try:
        parsed = ast.parse(expr, mode="eval")
        _safe(parsed)
        return _Eval(ctx).visit(parsed)
    except Exception as e:
        raise ValueError(f"Invalid rule expression '{expr}': {e}")

class _Eval(ast.NodeVisitor):
    def __init__(self, ctx: Dict[str, Any]):
        self.ctx = ctx

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_Name(self, node: ast.Name):
        if node.id in self.ctx:
            return self.ctx[node.id]
        if node.id in _ALLOWED_FUNCS:
            return _ALLOWED_FUNCS[node.id]
        raise NameError(node.id)

    def visit_Constant(self, node: ast.Constant):
        return node.value

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        return self._binop(type(node.op), left, right)

    def _binop(self, op, a, b):
        if op is ast.Add: return a + b
        if op is ast.Sub: return a - b
        if op is ast.Mult: return a * b
        if op is ast.Div: return a / b
        if op is ast.FloorDiv: return a // b
        if op is ast.Mod: return a % b
        if op is ast.Pow: return a ** b
        raise ValueError("Unsupported op")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not): return not operand
        if isinstance(node.op, ast.USub): return -operand
        if isinstance(node.op, ast.UAdd): return +operand
        raise ValueError("Unsupported unary op")

    def visit_BoolOp(self, node: ast.BoolOp):
        if isinstance(node.op, ast.And):
            val = True
            for v in node.values:
                val = val and bool(self.visit(v))
                if not val: break
            return val
        if isinstance(node.op, ast.Or):
            val = False
            for v in node.values:
                val = val or bool(self.visit(v))
                if val: break
            return val
        raise ValueError("Unsupported bool op")

    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq) and not (left == right): return False
            if isinstance(op, ast.NotEq) and not (left != right): return False
            if isinstance(op, ast.Lt) and not (left < right): return False
            if isinstance(op, ast.LtE) and not (left <= right): return False
            if isinstance(op, ast.Gt) and not (left > right): return False
            if isinstance(op, ast.GtE) and not (left >= right): return False
            if isinstance(op, ast.In) and not (left in right): return False
            if isinstance(op, ast.NotIn) and not (left not in right): return False
            left = right
        return True

    def visit_Call(self, node: ast.Call):
        fn = self.visit(node.func)
        if fn not in _ALLOWED_FUNCS.values():
            raise ValueError("Function not allowed")
        args = [self.visit(a) for a in node.args]
        kwargs = {kw.arg: self.visit(kw.value) for kw in node.keywords}
        return fn(*args, **kwargs)

    def visit_Attribute(self, node: ast.Attribute):
        value = self.visit(node.value)
        return getattr(value, node.attr)

    def visit_Subscript(self, node: ast.Subscript):
        value = self.visit(node.value)
        sl = self.visit(node.slice)
        return value[sl]

    def visit_Index(self, node: ast.Index):
        return self.visit(node.value)

def apply_rules(rules: dict, data_ctx: dict) -> dict:
    """Return a dict with sets: show, hide, lock, readonly derived from rule expressions.
    rules = {"show": [{"when": "mileage > 0", "targets": ["notes"]}], ...}
    """
    result = {"show": set(), "hide": set(), "lock": set(), "readonly": set()}
    if not rules:
        return result
    for action, items in rules.items():
        for item in items or []:
            cond = bool(eval_expr(item.get("when", "True"), data_ctx))
            if cond:
                for t in item.get("targets", []):
                    result.setdefault(action, set()).add(t)
    return result
