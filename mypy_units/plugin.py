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

# Fully-qualified name of our Quantity class.
_QUANTITY_FULLNAME = "mypy_units.quantity.Quantity"

# builtins that are always accepted as an escape hatch
_PLAIN_NUMERIC = {"builtins.float", "builtins.int", "builtins.complex"}


# ---------------------------------------------------------------------------
# Type-level helpers
# ---------------------------------------------------------------------------

def _unit_str(tp: Type) -> str | None:
    """Extract the literal unit/dim string from ``Quantity[Literal["..."]]``."""
    proper = get_proper_type(tp)
    if not isinstance(proper, Instance):
        return None
    if proper.type.fullname != _QUANTITY_FULLNAME:
        return None
    if not proper.args:
        return None
    arg = get_proper_type(proper.args[0])
    if isinstance(arg, LiteralType) and isinstance(arg.value, str):
        return arg.value
    return None


def _is_escape_hatch(tp: Type) -> bool:
    """Return True for plain float/int/Any — never flagged."""
    proper = get_proper_type(tp)
    if isinstance(proper, AnyType):
        return True
    if isinstance(proper, Instance) and proper.type.fullname in _PLAIN_NUMERIC:
        return True
    return False


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
# ``Quantity[Literal["<dim>"]]`` instead of ``Quantity[Any]``, so mypy can
# compare the final expression type against the declared return annotation and
# flag a mismatch as a ``[return-value]`` error.
#
# The dim strings are pint dimensionality strings, identical to those used as
# the Literal values in ``mypy_units.units``.
# ---------------------------------------------------------------------------

def _build_dim_quantity(ctx: MethodContext, dim_str: str) -> Type:
    """Return ``Quantity[Literal[dim_str]]`` reusing the LiteralType fallback."""
    proper = get_proper_type(ctx.type)
    if not isinstance(proper, Instance):
        return ctx.default_return_type  # type: ignore[return-value]
    if proper.args:
        existing = get_proper_type(proper.args[0])
        if isinstance(existing, LiteralType):
            lit = LiteralType(value=dim_str, fallback=existing.fallback)
            return proper.copy_modified(args=[lit, *proper.args[1:]])
    return ctx.default_return_type  # type: ignore[return-value]


def _make_arith_hook(op: str) -> Callable[[MethodContext], Type]:
    """Return a method hook that computes the result dimensionality for *op*.

    *op* is one of ``"*"``, ``"/"``, ``"/r"`` (reversed division, i.e.
    ``scalar / Quantity``), ``"+"`` / ``"-"`` (same dim), ``"unary"``.
    """
    def hook(ctx: MethodContext) -> Type:
        self_str = _unit_str(ctx.type)
        if self_str is None:
            return ctx.default_return_type  # type: ignore[return-value]

        self_dim = resolve(self_str)
        if self_dim is None:
            return ctx.default_return_type  # type: ignore[return-value]

        if op == "unary":
            return _build_dim_quantity(ctx, canonical_dim_str(self_dim))

        # Get the other operand's dim string (None if plain float/int)
        other_dim = None
        if ctx.arg_types and ctx.arg_types[0]:
            other_str = _unit_str(ctx.arg_types[0][0])
            if other_str is not None:
                other_dim = resolve(other_str)

        if op in ("+", "-"):
            # Dimensionality of result equals self; mismatched add/sub is
            # caught when the result is used (wrong dim propagates).
            return _build_dim_quantity(ctx, canonical_dim_str(self_dim))

        empty: DimDict = {}

        if op == "*":
            result = dim_mul(self_dim, other_dim if other_dim is not None else empty)
            return _build_dim_quantity(ctx, canonical_dim_str(result))

        if op == "/":
            result = dim_div(self_dim, other_dim if other_dim is not None else empty)
            return _build_dim_quantity(ctx, canonical_dim_str(result))

        if op == "/r":
            # scalar / self  →  dimensionless / self_dim
            numerator = other_dim if other_dim is not None else empty
            result = dim_div(numerator, self_dim)
            return _build_dim_quantity(ctx, canonical_dim_str(result))

        return ctx.default_return_type  # type: ignore[return-value]

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

        return _build_dim_quantity(ctx, canonical_dim_str(dim_pow(self_dim, exp)))

    return hook


# Map Quantity arithmetic method fullnames → their hooks.
_ARITH_HOOKS: dict[str, Callable[[MethodContext], Type]] = {
    f"{_QUANTITY_FULLNAME}.__add__":      _make_arith_hook("+"),
    f"{_QUANTITY_FULLNAME}.__radd__":     _make_arith_hook("+"),
    f"{_QUANTITY_FULLNAME}.__sub__":      _make_arith_hook("-"),
    f"{_QUANTITY_FULLNAME}.__rsub__":     _make_arith_hook("-"),
    f"{_QUANTITY_FULLNAME}.__mul__":      _make_arith_hook("*"),
    f"{_QUANTITY_FULLNAME}.__rmul__":     _make_arith_hook("*"),
    f"{_QUANTITY_FULLNAME}.__truediv__":  _make_arith_hook("/"),
    f"{_QUANTITY_FULLNAME}.__floordiv__": _make_arith_hook("/"),
    f"{_QUANTITY_FULLNAME}.__rtruediv__": _make_arith_hook("/r"),
    f"{_QUANTITY_FULLNAME}.__neg__":      _make_arith_hook("unary"),
    f"{_QUANTITY_FULLNAME}.__pos__":      _make_arith_hook("unary"),
    f"{_QUANTITY_FULLNAME}.__abs__":      _make_arith_hook("unary"),
    f"{_QUANTITY_FULLNAME}.__pow__":      _make_pow_hook(),
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
# Signature hook — widens Quantity[Literal["..."]] params to Quantity[Any]
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

def _make_quantity_type(template_tp: Type, dim_str: str) -> Type | None:
    """Build ``Quantity[Literal[dim_str]]`` using *template_tp* as a model."""
    proper = get_proper_type(template_tp)
    if not isinstance(proper, Instance):
        return None
    if proper.args:
        arg0 = get_proper_type(proper.args[0])
        if isinstance(arg0, LiteralType):
            lit = LiteralType(value=dim_str, fallback=arg0.fallback)
            return proper.copy_modified(args=[lit, *proper.args[1:]])
    return None


def _read_numeric_arg(
    context: object, arg_types: list[list[Type]], arg_idx: int
) -> int | float | None:
    """Extract a numeric literal from a call's arg at *arg_idx*.

    Works for both FunctionContext and MethodContext (pass ctx.context and
    ctx.arg_types respectively).
    """
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
        result = _make_quantity_type(base_tp, canonical_dim_str(result_dim))
        if result is None:
            return ctx.default_return_type  # type: ignore[return-value]
        return result
    return hook


def _make_numpy_unary_dim_hook(exp: Fraction) -> Callable[[FunctionContext], Type]:
    """Return a hook for unary functions where result dim = input dim ** exp."""
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
        result = _make_quantity_type(arg_tp, canonical_dim_str(result_dim))
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
#
# np.power is typed as _UFunc_Nin2_Nout1[Literal["power"], ...], so we hook
# _UFunc_Nin2_Nout1.__call__ and dispatch by the ufunc name in args[0].
# Similarly for _UFunc_Nin1_Nout1 (sqrt, cbrt).
# ---------------------------------------------------------------------------

_NP_UFUNC_PKG = "numpy._typing._ufunc"

# ufunc name -> (n_inputs, exponent_or_None)
# exponent_or_None: None means "read from arg 1" (for power)
_UFUNC_DIM_RULES: dict[str, tuple[int, Fraction | None]] = {
    "power":      (2, None),              # exp from arg 1
    "float_power": (2, None),             # same
    "sqrt":       (1, Fraction(1, 2)),
    "cbrt":       (1, Fraction(1, 3)),
    "square":     (1, Fraction(2)),
    "reciprocal": (1, Fraction(-1)),
}


def _ufunc_name_from_ctx(ctx: MethodContext) -> str | None:
    """Extract the ufunc name from ctx.type.args[0] (a Literal["name"])."""
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
            # read exponent from second argument
            raw_exp = _read_numeric_arg(ctx.context, ctx.arg_types, 1)
            if raw_exp is None:
                return ctx.default_return_type  # type: ignore[return-value]
            exp = float(raw_exp)
        else:
            exp = float(fixed_exp)

        result_dim = dim_pow(base_dim, exp)
        result = _make_quantity_type(base_tp, canonical_dim_str(result_dim))
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
