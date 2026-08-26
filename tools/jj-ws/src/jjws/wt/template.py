"""Small, deliberately limited template renderer for wt configuration."""

import hashlib
import re
import shlex
from collections.abc import Mapping


class TemplateError(ValueError):
    pass


_EXPRESSION = re.compile(r"{{\s*(.*?)\s*}}")
_VARIABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize(value: str) -> str:
    return value.replace("/", "-").replace("\\", "-")


def _short_hash(value: str) -> str:
    number = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "little")
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    return "".join(alphabet[(number // (36**index)) % 36] for index in range(3))


def sanitize_db(value: str) -> str:
    if not value:
        return ""
    base = re.sub(r"_+", "_", re.sub(r"[^a-z0-9]", "_", value.lower()))
    if base[:1].isdigit():
        base = f"_{base}"
    base = base[:44]
    if not base.endswith("_"):
        base += "_"
    return base + _short_hash(value)


def hash_port(value: str) -> str:
    number = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "little")
    return str(10000 + number % 10000)


_FILTERS = {
    "sanitize": sanitize,
    "sanitize_db": sanitize_db,
    "hash_port": hash_port,
}


def render(template: str, variables: Mapping[str, str], *, shell: bool = False) -> str:
    def replace(match: re.Match[str]) -> str:
        expression = match.group(1)
        parts = expression.rsplit("|", 1)
        value = _evaluate(parts[0].strip(), variables)
        if len(parts) == 2:
            filter_name = parts[1].strip()
            try:
                value = _FILTERS[filter_name](value)
            except KeyError as error:
                raise TemplateError(f"unknown filter '{filter_name}'") from error
        if not shell:
            return value
        quote = _shell_quote_at(template, match.start())
        if quote == "'":
            return value.replace("'", "'\"'\"'")
        if quote == '"':
            return re.sub(r'([\\"$`])', r"\\\1", value)
        return shlex.quote(value)

    return _EXPRESSION.sub(replace, template)


def _shell_quote_at(template: str, end: int) -> str | None:
    quote = None
    escaped = False
    comment = False
    for index, char in enumerate(template[:end]):
        if comment:
            if char == "\n":
                comment = False
            continue
        if escaped:
            escaped = False
        elif char == "\\" and quote != "'":
            escaped = True
        elif (
            quote is None
            and char == "#"
            and (
                index == 0
                or template[index - 1].isspace()
                or template[index - 1] in ";&|()<>"
            )
        ):
            comment = True
        elif quote is None and char in "'\"":
            quote = char
        elif char == quote:
            quote = None
    return quote


def _evaluate(expression: str, variables: Mapping[str, str]) -> str:
    while expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1].strip()

    values = []
    for part in re.split(r"\s*~\s*", expression):
        part = part.strip()
        if len(part) >= 2 and part[0] == part[-1] and part[0] in "'\"":
            values.append(part[1:-1])
        elif _VARIABLE.fullmatch(part):
            try:
                values.append(variables[part])
            except KeyError as error:
                raise TemplateError(f"unknown variable '{part}'") from error
        else:
            raise TemplateError(f"unsupported expression '{expression}'")
    return "".join(values)
