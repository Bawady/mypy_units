from __future__ import annotations

from collections.abc import Callable
from fractions import Fraction

from mypy.nodes import CallExpr, FloatExpr, FuncDef, IntExpr, MypyFile, OpExpr
from mypy.plugin import FunctionContext, FunctionSigContext, MethodContext, Plugin
from mypy.types import (
    AnyType,
    CallableType,
    Instance,
    LiteralType,
    Type,
    TypeOfAny,
    get_proper_type,
)

from mypy_units.dimension import (
    DimDict,
    canonical_dim_str,
    dim_div,
    dim_mul,
    dim_pow,
    dims_equal,
    resolve,
)

_NUMPY_MOD = "mypy_units.numpy"

_QUANTITY_FULLNAME = "mypy_units.quantity.Quantity"
_ARRAY_FULLNAME = "mypy_units.array_quantity.QuantityArray"

_PLAIN_NUMERIC = {"builtins.float", "builtins.int", "builtins.complex"}


# ---------------------------------------------------------------------------
# Type-level helpers
# ---------------------------------------------------------------------------

def _unit_str(tp: Type) -> str | None:
    """Extract the dimension string from Quantity[Literal["…"]] or
    QuantityArray[Quantity[Literal["…"]]]."""
    proper = get_proper_type(tp)
    if not isinstance(proper, Instance):
        return None

    if proper.type.fullname == _QUANTITY_FULLNAME:
        if not proper.args:
            return None
        arg = get_proper_type(proper.args[0])
        if isinstance(arg, LiteralType) and isinstance(arg.value, str):
            return arg.value
        return None

    if proper.type.fullname == _ARRAY_FULLNAME:
        if not proper.args:
            return None
        return _unit_str(proper.args[0])  # unwrap the inner Quantity layer

    return None


def _is_array_type(tp: Type) -> bool:
    proper = get_proper_type(tp)
    return isinstance(proper, Instance) and proper.type.fullname == _ARRAY_FULLNAME


def _is_escape_hatch(tp: Type) -> bool:
    proper = get_proper_type(tp)
    if isinstance(proper, AnyType):
        return True
    if isinstance(proper, Instance) and proper.type.fullname in _PLAIN_NUMERIC:
        return True
    return False


# ---------------------------------------------------------------------------
# Unified result-type builder
#
# Given a *template* type (Quantity[Literal["old"]] or
# QuantityArray[Quantity[Literal["old"]]]) and a new dimension string,
# returns the same wrapper class carrying the new dimension, or None when
# the template has an unexpected structure.
# ---------------------------------------------------------------------------

def _make_dim_type(template: Type, dim_str: str) -> Type | None:
    proper = get_proper_type(template)
    if not isinstance(proper, Instance):
        return None

    if proper.type.fullname == _QUANTITY_FULLNAME:
        if proper.args:
            arg0 = get_proper_type(proper.args[0])
            if isinstance(arg0, LiteralType):
                lit = LiteralType(value=dim_str, fallback=arg0.fallback)
                return proper.copy_modified(args=[lit, *proper.args[1:]])

    elif proper.type.fullname == _ARRAY_FULLNAME:
        if proper.args:
            inner = get_proper_type(proper.args[0])
            if (
                isinstance(inner, Instance)
                and inner.type.fullname == _QUANTITY_FULLNAME
                and inner.args
            ):
                arg0 = get_proper_type(inner.args[0])
                if isinstance(arg0, LiteralType):
                    lit = LiteralType(value=dim_str, fallback=arg0.fallback)
                    new_inner = inner.copy_modified(args=[lit])
                    return proper.copy_modified(args=[new_inner])

    return None


# ---------------------------------------------------------------------------
# Core dimension check (call-site)
# ---------------------------------------------------------------------------

def _check_call(
    ctx: FunctionContext | MethodContext,
    callee_type: CallableType,
) -> Type:
    for i, (formal_type, param_name) in enumerate(
        zip(callee_type.arg_types, callee_type.arg_names, strict=False)
    ):
        expected_str = _unit_str(formal_type)
        if expected_str is None:
            continue

        if i >= len(ctx.arg_types) or not ctx.arg_types[i]:
            continue

        actual_type = ctx.arg_types[i][0]

        if _is_escape_hatch(actual_type):
            continue

        actual_str = _unit_str(actual_type)
        if actual_str is None:
            continue

        expected_dim = resolve(expected_str)
        actual_dim = resolve(actual_str)

        if expected_dim is None or actual_dim is None:
            continue

        if not dims_equal(expected_dim, actual_dim):
            label = param_name if param_name else str(i)
            ctx.api.fail(
                f"Dimension mismatch for argument '{label}': "
                f"expected {expected_dim}, got {actual_dim}",
                ctx.context,
            )

    return ctx.default_return_type  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Callee type lookup
# ---------------------------------------------------------------------------

def _callee_callable(
    ctx: FunctionContext | MethodContext, fullname: str
) -> CallableType | None:
    parts = fullname.rsplit(".", 1)
    if len(parts) != 2:
        return None
    mod_name, func_name = parts
    modules: dict[str, MypyFile] = getattr(ctx.api, "modules", {})
    mod = modules.get(mod_name)
    if mod is None:
        return None
    sym = mod.names.get(func_name)
    if sym is None or not isinstance(sym.node, FuncDef):
        return None
    t = sym.node.type
    return t if isinstance(t, CallableType) else None


# ---------------------------------------------------------------------------
# Arithmetic method hooks — track dimensionality through expressions
#
# When mypy type-checks a function body it uses the inferred type of each
# sub-expression.  These hooks make arithmetic operators return a concrete
# Quantity[Literal["<dim>"]] (or QuantityArray[Quantity[Literal["<dim>"]]])
# instead of Quantity[Any], so mypy can compare the final expression type
# against the declared return annotation and flag mismatches.
#
# Cross-type rule: if either operand is a QuantityArray, the result is a
# QuantityArray (matching numpy broadcasting semantics).
# ---------------------------------------------------------------------------

def _make_arith_hook(op: str) -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        self_str = _unit_str(ctx.type)
        if self_str is None:
            return ctx.default_return_type  # type: ignore[return-value]

        self_dim = resolve(self_str)
        if self_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]

        if op == "unary":
            dim_str = canonical_dim_str(self_dim)
            result = _make_dim_type(ctx.type, dim_str)
            return result if result is not None else ctx.default_return_type  # type: ignore[return-value]

        other_dim = None
        other_tp: Type | None = None
        if ctx.arg_types and ctx.arg_types[0]:
            other_tp = ctx.arg_types[0][0]
            other_str = _unit_str(other_tp)
            if other_str is not None:
                other_dim = resolve(other_str)

        empty: DimDict = {}

        if op in ("+", "-"):
            result_dim = self_dim
        elif op == "*":
            result_dim = dim_mul(self_dim, other_dim if other_dim is not None else empty)
        elif op == "/":
            result_dim = dim_div(self_dim, other_dim if other_dim is not None else empty)
        elif op == "/r":
            numerator = other_dim if other_dim is not None else empty
            result_dim = dim_div(numerator, self_dim)
        else:
            return ctx.default_return_type  # type: ignore[return-value]

        dim_str = canonical_dim_str(result_dim)

        # When self is a scalar Quantity but other is a QuantityArray, use
        # the array operand as the result template so the return type is
        # QuantityArray rather than Quantity.
        if (
            not _is_array_type(ctx.type)
            and other_tp is not None
            and _is_array_type(other_tp)
        ):
            result = _make_dim_type(other_tp, dim_str)
            if result is not None:
                return result

        result = _make_dim_type(ctx.type, dim_str)
        return result if result is not None else ctx.default_return_type  # type: ignore[return-value]

    return hook


def _make_pow_hook() -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        self_str = _unit_str(ctx.type)
        if self_str is None:
            return ctx.default_return_type  # type: ignore[return-value]
        self_dim = resolve(self_str)
        if self_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]

        # mypy widens integer literals to int when the param is int|float,
        # so we read the exponent directly from the AST instead.
        exp: int | None = None
        if isinstance(ctx.context, OpExpr) and isinstance(ctx.context.right, IntExpr):
            exp = ctx.context.right.value
        if exp is None:
            return ctx.default_return_type  # type: ignore[return-value]

        dim_str = canonical_dim_str(dim_pow(self_dim, exp))
        result = _make_dim_type(ctx.type, dim_str)
        return result if result is not None else ctx.default_return_type  # type: ignore[return-value]

    return hook


def _arith_hooks_for(fullname: str) -> dict[str, Callable[[MethodContext], Type]]:
    return {
        f"{fullname}.__add__":      _make_arith_hook("+"),
        f"{fullname}.__radd__":     _make_arith_hook("+"),
        f"{fullname}.__sub__":      _make_arith_hook("-"),
        f"{fullname}.__rsub__":     _make_arith_hook("-"),
        f"{fullname}.__mul__":      _make_arith_hook("*"),
        f"{fullname}.__rmul__":     _make_arith_hook("*"),
        f"{fullname}.__truediv__":  _make_arith_hook("/"),
        f"{fullname}.__floordiv__": _make_arith_hook("/"),
        f"{fullname}.__rtruediv__": _make_arith_hook("/r"),
        f"{fullname}.__neg__":      _make_arith_hook("unary"),
        f"{fullname}.__pos__":      _make_arith_hook("unary"),
        f"{fullname}.__abs__":      _make_arith_hook("unary"),
        f"{fullname}.__pow__":      _make_pow_hook(),
    }


_ARITH_HOOKS: dict[str, Callable[[MethodContext], Type]] = {
    **_arith_hooks_for(_QUANTITY_FULLNAME),
    **_arith_hooks_for(_ARRAY_FULLNAME),
}


# ---------------------------------------------------------------------------
# Hook factories (call-site checks)
# ---------------------------------------------------------------------------

def _make_function_hook(fullname: str) -> Callable[[FunctionContext], Type]:
    def hook(ctx: FunctionContext) -> Type:
        callee = _callee_callable(ctx, fullname)
        if callee is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return _check_call(ctx, callee)

    return hook


def _make_method_hook(fullname: str) -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        callee = _callee_callable(ctx, fullname)
        if callee is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return _check_call(ctx, callee)

    return hook


# ---------------------------------------------------------------------------
# Signature hook — widens Quantity[Literal["…"]] and
# QuantityArray[Quantity[Literal["…"]]] params to Quantity[Any] /
# QuantityArray[Any] so mypy never emits spurious [arg-type] errors before
# the plugin's own dimension check runs.
# ---------------------------------------------------------------------------

def _make_sig_hook(fullname: str) -> Callable[[FunctionSigContext], CallableType]:
    def hook(ctx: FunctionSigContext) -> CallableType:
        sig = ctx.default_signature
        if not any(_unit_str(tp) is not None for tp in sig.arg_types):
            return sig
        any_type = AnyType(TypeOfAny.special_form)

        def _widen(tp: Type) -> Type:
            if _unit_str(tp) is None:
                return tp
            proper = get_proper_type(tp)
            if isinstance(proper, Instance):
                return proper.copy_modified(args=[any_type])
            return tp

        return sig.copy_modified(arg_types=[_widen(tp) for tp in sig.arg_types])

    return hook


# ---------------------------------------------------------------------------
# NumPy function hooks — dimension-aware wrappers in mypy_units.numpy
# ---------------------------------------------------------------------------

def _read_numeric_arg(
    context: object, arg_types: list[list[Type]], arg_idx: int
) -> int | float | None:
    if len(arg_types) > arg_idx and arg_types[arg_idx]:
        tp = get_proper_type(arg_types[arg_idx][0])
        if isinstance(tp, LiteralType) and isinstance(tp.value, (int, float)):
            return tp.value
    if isinstance(context, CallExpr) and len(context.args) > arg_idx:
        node = context.args[arg_idx]
        if isinstance(node, IntExpr):
            return node.value
        if isinstance(node, FloatExpr):
            return float(node.value)
    return None


def _make_numpy_power_hook() -> Callable[[FunctionContext], Type]:
    def hook(ctx: FunctionContext) -> Type:
        if not ctx.arg_types or not ctx.arg_types[0]:
            return ctx.default_return_type  # type: ignore[return-value]
        base_tp = ctx.arg_types[0][0]
        base_str = _unit_str(base_tp)
        if base_str is None:
            return ctx.default_return_type  # type: ignore[return-value]
        base_dim = resolve(base_str)
        if base_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]
        exp = _read_numeric_arg(ctx.context, ctx.arg_types, 1)
        if exp is None:
            return ctx.default_return_type  # type: ignore[return-value]
        result_dim = dim_pow(base_dim, exp)
        result = _make_dim_type(base_tp, canonical_dim_str(result_dim))
        if result is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return result
    return hook


def _make_numpy_unary_dim_hook(exp: Fraction) -> Callable[[FunctionContext], Type]:
    def hook(ctx: FunctionContext) -> Type:
        if not ctx.arg_types or not ctx.arg_types[0]:
            return ctx.default_return_type  # type: ignore[return-value]
        arg_tp = ctx.arg_types[0][0]
        arg_str = _unit_str(arg_tp)
        if arg_str is None:
            return ctx.default_return_type  # type: ignore[return-value]
        arg_dim = resolve(arg_str)
        if arg_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]
        result_dim = dim_pow(arg_dim, float(exp))
        result = _make_dim_type(arg_tp, canonical_dim_str(result_dim))
        if result is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return result
    return hook


_NUMPY_FUNCTION_HOOKS: dict[str, Callable[[FunctionContext], Type]] = {
    f"{_NUMPY_MOD}.power": _make_numpy_power_hook(),
    f"{_NUMPY_MOD}.sqrt":  _make_numpy_unary_dim_hook(Fraction(1, 2)),
    f"{_NUMPY_MOD}.cbrt":  _make_numpy_unary_dim_hook(Fraction(1, 3)),
}

# ---------------------------------------------------------------------------
# NumPy ufunc method hooks — hooks np.power / np.sqrt / np.cbrt directly
# ---------------------------------------------------------------------------

_NP_UFUNC_PKG = "numpy._typing._ufunc"

_UFUNC_DIM_RULES: dict[str, tuple[int, Fraction | None]] = {
    "power":      (2, None),
    "float_power": (2, None),
    "sqrt":       (1, Fraction(1, 2)),
    "cbrt":       (1, Fraction(1, 3)),
    "square":     (1, Fraction(2)),
    "reciprocal": (1, Fraction(-1)),
}


def _ufunc_name_from_ctx(ctx: MethodContext) -> str | None:
    proper = get_proper_type(ctx.type)
    if not isinstance(proper, Instance) or not proper.args:
        return None
    name_tp = get_proper_type(proper.args[0])
    if isinstance(name_tp, LiteralType) and isinstance(name_tp.value, str):
        return name_tp.value
    return None


def _make_ufunc_call_hook() -> Callable[[MethodContext], Type]:
    def hook(ctx: MethodContext) -> Type:
        ufunc_name = _ufunc_name_from_ctx(ctx)
        if ufunc_name is None or ufunc_name not in _UFUNC_DIM_RULES:
            return ctx.default_return_type  # type: ignore[return-value]

        n_inputs, fixed_exp = _UFUNC_DIM_RULES[ufunc_name]

        if not ctx.arg_types or not ctx.arg_types[0]:
            return ctx.default_return_type  # type: ignore[return-value]
        base_tp = ctx.arg_types[0][0]
        base_str = _unit_str(base_tp)
        if base_str is None:
            return ctx.default_return_type  # type: ignore[return-value]
        base_dim = resolve(base_str)
        if base_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]

        if fixed_exp is None:
            raw_exp = _read_numeric_arg(ctx.context, ctx.arg_types, 1)
            if raw_exp is None:
                return ctx.default_return_type  # type: ignore[return-value]
            exp = float(raw_exp)
        else:
            exp = float(fixed_exp)

        result_dim = dim_pow(base_dim, exp)
        result = _make_dim_type(base_tp, canonical_dim_str(result_dim))
        if result is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return result

    return hook


_UFUNC_CALL_HOOK = _make_ufunc_call_hook()

_NUMPY_UFUNC_HOOKS: dict[str, Callable[[MethodContext], Type]] = {
    f"{_NP_UFUNC_PKG}._UFunc_Nin2_Nout1.__call__": _UFUNC_CALL_HOOK,
    f"{_NP_UFUNC_PKG}._UFunc_Nin1_Nout1.__call__": _UFUNC_CALL_HOOK,
}


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------

class PintUnitsPlugin(Plugin):
    def get_function_signature_hook(
        self, fullname: str
    ) -> Callable[[FunctionSigContext], CallableType] | None:
        return _make_sig_hook(fullname)

    def get_function_hook(
        self, fullname: str
    ) -> Callable[[FunctionContext], Type] | None:
        if fullname in _NUMPY_FUNCTION_HOOKS:
            return _NUMPY_FUNCTION_HOOKS[fullname]
        return _make_function_hook(fullname)

    def get_method_hook(
        self, fullname: str
    ) -> Callable[[MethodContext], Type] | None:
        if fullname in _ARITH_HOOKS:
            return _ARITH_HOOKS[fullname]
        if fullname in _NUMPY_UFUNC_HOOKS:
            return _NUMPY_UFUNC_HOOKS[fullname]
        return _make_method_hook(fullname)


def plugin(version: str) -> type[PintUnitsPlugin]:
    return PintUnitsPlugin
