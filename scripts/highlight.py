#!/usr/bin/env python3
"""Syntax highlighting for the code blocks of a reviewed document.

`highlight(language, code)` returns a bare HTML *fragment*: token ranges are
wrapped in `<span class="tok-…">` and everything else comes back as escaped
text with no wrapper at all, because the page owns the surrounding
`<code>`/`<pre>` element.  The five class names -- `tok-com`, `tok-str`,
`tok-num`, `tok-kw`, `tok-bi` -- are the whole vocabulary, since they are
exactly what the page's stylesheet selects; a sixth name would be coloured by
nothing.

The security property is an ordering one rather than a filter: `_scan` finds
token *ranges*, `_escape` runs over the source, and only the escaped text is
wrapped afterwards.  A token whose contents are `</span><script>` therefore
cannot break out of its span, and no source character reaches the output as a
raw `<`, `>` or `&`.  `tests/test_highlight.py` pins that ordering by taking
the spans back off the output and un-escaping the remainder to the source.

The languages differ only in data.  `_LANGUAGES` below is the entire table: the
line-comment marker, the block-comment delimiters, the string quote characters
with the escape mode each one uses, and the keyword and builtin sets.  One
routine, `_scan`, walks the text for all of them with four explicit states --
normal, line comment, block comment, string -- so an unterminated construct has
exactly one exit: the literal scan runs to the end of the input and the rest of
the text becomes that token.  Every step either consumes a character or ends
the scan, so the walk cannot loop.

`language` is the info string of a fenced block: a hint, not a promise.  It is
lower-cased, trimmed and read up to its first whitespace, so `js` and
`js title="x"` mean the same thing.  An empty, unknown or `text` hint returns
the escaped code with no spans at all -- no guessing, and no partial
tokenization of a language that is not fully handled.  Nothing here raises: a
review page that cannot highlight a block still has to render it.
"""
from __future__ import annotations

import functools

# Escape modes.  A mode belongs to a quote character, not to a language, which
# is what lets one string routine serve shell single quotes (no escapes), Go raw
# strings (no escapes) and SQL (a doubled quote) alongside everything else.
_BACKSLASH = "backslash"  # `\x` is an escaped character
_PLAIN = "plain"          # the next matching quote closes the literal
_DOUBLED = "doubled"      # `''` is an escaped quote, not the end of the literal

# Token classes, spelled exactly as the page's stylesheet expects them.
_COM = "com"
_STR = "str"
_NUM = "num"
_KW = "kw"
_BI = "bi"

# The four scanner states.
_NORMAL = "normal"
_LINE = "line"
_BLOCK = "block"
_STRING = "string"

_DIGITS = "0123456789"
# A digit separator or a unit suffix (`1_000`, `10u8`) is consumed by the number
# scanner itself, so no language table has to say anything about numbers.
_UNDERSCORE = "_"
# A Rust character literal is one character or one short escape (`'\n'`,
# `'\''`); beyond this distance a quote is a lifetime, so the text stays plain.
_CHAR_BODY = 4

_NO_BLOCK = ("", "")
_NO_WORDS = frozenset()


def _escape(text: str) -> str:
    """HTML-escape; `&` first so the escapes introduced below stay literal."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Languages -----------------------------------------------------------------
# One entry per supported language.  Missing keys come from `_DEFAULTS`, so a
# spec lists only what makes it different.  `_scan` indexes these directly.

_JAVASCRIPT = {
    "line": "//",
    "block": ("/*", "*/"),
    "quotes": {"'": _BACKSLASH, '"': _BACKSLASH, "`": _BACKSLASH},
    "ident": "$",  # `$id` is an ordinary JavaScript identifier
    "keywords": frozenset(
        """
        as async await break case catch class const continue debugger default delete
        do else export extends false finally for from function get if implements in
        instanceof interface let new null of package private protected public readonly
        return satisfies set static super switch this throw true try typeof var void
        while with yield
        """.split()
    ),
    "builtins": frozenset(
        """
        Array Boolean Date Error Function JSON Map Math Number Object Promise RegExp
        Set String Symbol console document exports globalThis module process require
        undefined window
        """.split()
    ),
}

_LANGUAGES: dict[str, dict] = {
    "python": {
        "line": "#",
        "quotes": {"'": _BACKSLASH, '"': _BACKSLASH},
        "triple": "\"'",  # these quotes also open a triple-quoted literal
        "keywords": frozenset(
            """
            and as assert async await break class continue def del elif else except
            finally for from global if import in is lambda nonlocal not or pass raise
            return try while with yield
            """.split()
        ),
        "builtins": frozenset(
            """
            False None True Exception IndexError KeyError RuntimeError TypeError
            ValueError abs all any bool bytes dict dir enumerate filter float format
            frozenset getattr hasattr hash input int isinstance issubclass iter len
            list map max min next object open print range repr reversed round set
            setattr slice sorted str sum super tuple type vars zip
            """.split()
        ),
    },
    "javascript": _JAVASCRIPT,
    "typescript": {
        **_JAVASCRIPT,
        "keywords": _JAVASCRIPT["keywords"]
        | frozenset("abstract declare enum infer is keyof override type".split())
        | frozenset("any bigint boolean never number object string symbol unknown void".split()),
        "builtins": _JAVASCRIPT["builtins"]
        | frozenset("Awaited Exclude Extract Omit Parameters Partial Pick Readonly Record ReturnType".split()),
    },
    "rust": {
        "line": "//",
        "block": ("/*", "*/"),
        "quotes": {"'": _BACKSLASH, '"': _BACKSLASH},
        "char": "'",  # a quote that does not close soon is a lifetime
        "keywords": frozenset(
            """
            as async await break const continue crate dyn else enum extern false fn
            for if impl in let loop match mod move mut pub ref return self Self static
            struct super trait true type union unsafe use where while
            """.split()
        ),
        "builtins": frozenset(
            """
            Box Cow Err None Ok Option Result Some String Vec bool char f32 f64 i128
            i16 i32 i64 i8 isize str u128 u16 u32 u64 u8 usize
            """.split()
        ),
    },
    "go": {
        "line": "//",
        "block": ("/*", "*/"),
        "quotes": {'"': _BACKSLASH, "`": _PLAIN},  # a backtick string is raw
        "types": True,  # a capitalised word is a builtin type name
        "keywords": frozenset(
            """
            break case chan const continue default defer else fallthrough false for func
            go goto if import interface map package range return select struct switch
            true type var
            """.split()
        ),
        "builtins": frozenset(
            """
            any bool byte comparable complex128 complex64 error float32 float64 int
            int8 int16 int32 int64 nil rune string uint uint8 uint16 uint32 uint64
            uintptr
            """.split()
        ),
    },
    "json": {
        # No comments in valid JSON; both forms are accepted so a stray one in a
        # pasted snippet does not colour the rest of the file as a string.
        "line": "//",
        "block": ("/*", "*/"),
        "quotes": {'"': _BACKSLASH},
        "builtins": frozenset(["false", "null", "true"]),
    },
    "yaml": {
        "line": "#",
        "boundary": True,  # `http://x#f` is a scalar, not a comment
        "quotes": {"'": _BACKSLASH, '"': _BACKSLASH},
        "ident": "~",  # `null` may be written as a bare tilde
        "builtins": frozenset(["false", "no", "null", "off", "on", "true", "yes", "~"]),
    },
    "shell": {
        "line": "#",
        "quotes": {"'": _PLAIN, '"': _BACKSLASH, "`": _PLAIN},
        "keywords": frozenset(
            """
            case do done elif else esac exit fi for function if in return select then
            time until while
            """.split()
        ),
        "builtins": frozenset(
            "cd echo export false printf pwd read set test true".split()
        ),
    },
    "sql": {
        "line": "--",
        "block": ("/*", "*/"),
        "quotes": {"'": _DOUBLED},
        "fold": True,  # SQL keywords are written in any case
        "keywords": frozenset(
            """
            add all alter and as asc between by case cast check column commit constraint
            create cross default delete desc distinct drop else end exists foreign from
            full group having in index inner insert into is join key left limit not
            offset on or order outer primary references rename replace return right
            rollback select set table then union unique update values view when where
            with
            """.split()
        ),
        "builtins": frozenset(["false", "null", "true"]),
    },
}

# Every spec reads the same keys, so a language lists only what it changes.
_DEFAULTS = {
    "line": "",
    "boundary": False,
    "block": _NO_BLOCK,
    "quotes": {},
    "triple": "",
    "char": "",
    "ident": "",
    "types": False,
    "fold": False,
    "keywords": _NO_WORDS,
    "builtins": _NO_WORDS,
}
_SPECS = {name: {**_DEFAULTS, **fields} for name, fields in _LANGUAGES.items()}

# The hint a fence carries is a name, not a language: the empty target is the
# deliberate "no highlighting" entry.
_ALIASES = {
    "bash": "shell",
    "go": "go",
    "golang": "go",
    "js": "javascript",
    "json": "json",
    "plain": "",
    "plaintext": "",
    "py": "python",
    "python": "python",
    "rs": "rust",
    "rust": "rust",
    "sh": "shell",
    "shell": "shell",
    "sql": "sql",
    "text": "",
    "ts": "typescript",
    "txt": "",
    "typescript": "typescript",
    "yaml": "yaml",
    "yml": "yaml",
    "zsh": "shell",
}
# Trailing punctuation a fence author may have left on the hint.
_TRIM = "{}.,;:!?"


def _resolve(hint: str) -> dict | None:
    """The spec for a fence info string, or None when there is nothing to do.

    Only the leading word is read, so `js`, `JS ` and `js title="x"` all mean
    the same thing; an empty, unknown or `text` hint resolves to None rather
    than to a guess.
    """
    words = hint.strip().lower().split()
    if not words:
        return None
    name = words[0].strip(_TRIM)
    if name in _ALIASES:
        name = _ALIASES[name]
    return _SPECS.get(name)


# The scan ------------------------------------------------------------------
# Everything below walks the source once.  A state either consumes a character
# or runs to the end of the input, so there is no way to stand still.

def _number_end(code: str, i: int) -> int:
    """Index just past the numeric literal that starts at `i`."""
    n = len(code)
    if code[i] in _DIGITS and code.startswith(("0x", "0X", "0b", "0B", "0o", "0O"), i):
        j = i + 2
        while j < n and (code[j] in _DIGITS or code[j].lower() in "abcdef" or code[j] == _UNDERSCORE):
            j += 1
        return j
    j = i
    while j < n and (code[j] in _DIGITS or code[j] == _UNDERSCORE):
        j += 1
    if code.startswith(".", j) and j + 1 < n and code[j + 1] in _DIGITS:
        j += 1
        while j < n and (code[j] in _DIGITS or code[j] == _UNDERSCORE):
            j += 1
    if j < n and code[j] in "eE":  # an exponent only counts with its digits
        k = j + 1
        if k < n and code[k] in "+-":
            k += 1
        if k < n and code[k] in _DIGITS:
            while k < n and (code[k] in _DIGITS or code[k] == _UNDERSCORE):
                k += 1
            j = k
    if j < n and (code[j].isalpha() or code[j] == _UNDERSCORE):
        # A unit or magnitude suffix rides along with its number: `10n`, `3.5f32`.
        while j < n and (code[j].isalnum() or code[j] == _UNDERSCORE):
            j += 1
    return j


def _escaped_end(code: str, start: int, delim: str) -> int:
    """Index just past the delimiter that closes the literal opened at `start`.

    An unterminated literal returns the end of the input, which is the one exit
    an unterminated construct needs: the rest of the text is that token.
    """
    i = start + len(delim)
    n = len(code)
    while i < n:
        if code[i] == "\\":
            i += 2  # an escaped character, even at the very end
            continue
        if code.startswith(delim, i):
            return i + len(delim)
        i += 1
    return n


def _doubled_end(code: str, start: int, delim: str) -> int:
    """Like `_escaped_end` for SQL, where `''` is one escaped quote."""
    i = start + len(delim)
    n = len(code)
    step = len(delim)
    while i < n:
        cut = code.find(delim, i)
        if cut < 0:
            return n
        if code.startswith(delim, cut + step):
            i = cut + 2 * step  # a doubled quote is content, not the close
            continue
        return cut + step
    return n


def _scan(spec: dict, code: str) -> list[tuple[str, str | None]]:
    """Split `code` into `(text, kind)` runs, in order; `kind` is None for plain
    text.  Ranges only -- the caller escapes, then wraps."""
    parts: list[tuple[str, str | None]] = []
    plain = 0  # start of the pending plain run
    state = _NORMAL
    delim = ""
    mode = _PLAIN

    def emit(start: int, end: int, kind: str) -> None:
        """Close the pending plain run and record one token."""
        nonlocal plain
        if start > plain:
            parts.append((code[plain:start], None))
        parts.append((code[start:end], kind))
        plain = end

    i = 0
    n = len(code)
    while i < n:
        if state == _LINE:
            cut = code.find("\n", i)
            emit(i, n if cut < 0 else cut, _COM)
            i = n if cut < 0 else cut
            state = _NORMAL
            continue
        if state == _BLOCK:
            close = spec["block"][1]
            cut = code.find(close, i + len(spec["block"][0]))
            emit(i, n if cut < 0 else cut + len(close), _COM)
            i = n if cut < 0 else cut + len(close)
            state = _NORMAL
            continue
        if state == _STRING:
            if mode == _BACKSLASH:
                cut = _escaped_end(code, i, delim)
            elif mode == _DOUBLED:
                cut = _doubled_end(code, i, delim)
            else:
                cut = code.find(delim, i + len(delim))
                cut = n if cut < 0 else cut + len(delim)
            emit(i, cut, _STR)
            i = cut
            state = _NORMAL
            continue

        # normal
        ch = code[i]
        if spec["line"] and code.startswith(spec["line"], i) and (
            not spec["boundary"] or i == 0 or code[i - 1] in " \t"
        ):
            state = _LINE
            continue
        open_block = spec["block"][0]
        if open_block and code.startswith(open_block, i):
            state = _BLOCK  # the opener belongs to the comment, not to the text
            continue
        if ch in spec["quotes"]:
            if ch in spec["triple"] and code.startswith(ch * 3, i):
                delim = ch * 3
                mode = _BACKSLASH
            elif ch == spec["char"] and code.find(ch, i + 1, i + 1 + _CHAR_BODY) < 0:
                i += 1  # a lifetime, not a character literal: ordinary text
                continue
            else:
                delim = ch
                mode = spec["quotes"][ch]
            state = _STRING
            continue
        if ch in _DIGITS or (ch == "." and i + 1 < n and code[i + 1] in _DIGITS):
            cut = _number_end(code, i)
            emit(i, cut, _NUM)
            i = cut
            continue
        if ch.isalpha() or ch == _UNDERSCORE or ch in spec["ident"]:
            j = i + 1
            while j < n and (code[j].isalnum() or code[j] == _UNDERSCORE):
                j += 1
            word = code[i:j]
            key = word.lower() if spec["fold"] else word
            if key in spec["keywords"]:
                emit(i, j, _KW)
            elif key in spec["builtins"] or (spec["types"] and word[0].isupper()):
                emit(i, j, _BI)
            i = j
            continue
        i += 1  # ordinary text, absorbed by the pending plain run

    if plain < n:
        parts.append((code[plain:], None))
    return parts


def _wrap(text: str, kind: str | None) -> str:
    """Escape, then wrap: the span is built from the escaped text only, so a
    token can never carry raw markup out of its own element."""
    escaped = _escape(text)
    if kind is None:
        return escaped
    return f'<span class="tok-{kind}">{escaped}</span>'


@functools.lru_cache(maxsize=512)
def _render(hint: str, code: str) -> str:
    spec = _resolve(hint)
    if spec is None:
        return _escape(code)
    return "".join(_wrap(text, kind) for text, kind in _scan(spec, code))


def highlight(language: str, code: str) -> str:
    """`code` as an HTML fragment, token ranges wrapped in `tok-*` spans.

    `language` is a fenced block's info string, read up to its first
    whitespace.  An empty, unknown or `text` hint returns the escaped code with
    no spans at all, and the result is deterministic: the same arguments always
    produce the same fragment, and nothing is carried between calls.

    Malformed input never raises -- a page that cannot highlight a block still
    has to render it, so the worst case is the escaped code.  A `code` that is
    not a string has no source text to render and comes back empty; a
    `language` that is not a string is treated as no hint.
    """
    try:
        text = code if isinstance(code, str) else ""
        hint = language if isinstance(language, str) else ""
        return _render(hint, text)
    except Exception:
        return _escape(code) if isinstance(code, str) else ""
