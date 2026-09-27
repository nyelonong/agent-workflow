from __future__ import annotations

from pathlib import Path
import re
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import highlight  # noqa: E402  (the tokenizer lives in scripts/ and is not a package)

CLASSES = {"com", "str", "num", "kw", "bi"}  # the page's stylesheet knows these five
SPAN = re.compile(r'<span class="tok-(\w+)">(.*?)</span>', re.S)


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def unescape(text: str) -> str:
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def parts(html: str) -> list[tuple[str | None, str]]:
    """The fragment as `(class, text)` runs in order; class is None for plain text."""
    out: list[tuple[str | None, str]] = []
    at = 0
    for match in SPAN.finditer(html):
        if match.start() > at:
            out.append((None, html[at : match.start()]))
        out.append((match.group(1), match.group(2)))
        at = match.end()
    if at < len(html):
        out.append((None, html[at:]))
    return out


def tokens(html: str) -> list[tuple[str, str]]:
    """Only the token runs, unescaped, in order."""
    return [(kind, unescape(text)) for kind, text in parts(html) if kind is not None]


# One snippet per language carrying every construct at once -- a comment, a
# string with an escape in it, a number, keywords, and a `<script>` payload --
# used by the invariants every language has to satisfy.
MIXED = {
    "python": 'def f(x):\n    s = "</span><script>alert(1)</script>"\n    return x + 1  # tail\n',
    "javascript": "const s = `a ${b} \"c\"`; // <script>\nconsole.log(0x1f, true);\n",
    "typescript": 'type A = { b: string };\nconst x: A = { b: "y" }; // <script>\n',
    "rust": "/* <script> */\nfn f<'a>(x: &'a str) -> u32 { let c = '<'; 42u32 }\n",
    "go": 'package main // <script>\nfunc main() { s := `a "b`; var n int = 0x1f; _ = s; _ = n }\n',
    "json": '{\n  "a": "b\\"c",  // <script>\n  "n": 1.5e3,\n  "t": true\n}\n',
    "yaml": 'url: http://x#frag  # <script>\nk: "a\\"b"\nn: 42\n',
    "shell": '#!/bin/sh  # <script>\necho "a\\"b" \'$HOME\' `date`\n',
    "sql": "SELECT 'a--b' /* <script> */ FROM t WHERE n > 1e3;\n",
}

# Every alias the contract promises, against the language it must resolve to.
ALIASES = {
    "python": ("py", "python"),
    "javascript": ("js", "javascript"),
    "typescript": ("ts", "typescript"),
    "rust": ("rs", "rust"),
    "go": ("go", "golang"),
    "shell": ("sh", "bash", "shell", "zsh"),
    "yaml": ("yml", "yaml"),
    "json": ("json",),
    "sql": ("sql",),
}
# Hints that mean "leave it alone", and languages the table must not guess at.
UNHIGHLIGHTED = ("", "   ", "text", "txt", "plaintext", "plain")
UNSUPPORTED = ("c", "diff", "cobol", "elixir", "kotlin", "swift", "php", "1c")


# The same bar for every language: given a fragment, the tokens are these, in
# this order.  A language that colours the wrong range, or splits one string in
# two, fails its own row of the table rather than a shared rule.
FRAGMENTS: dict[str, list[tuple[str, str, list[tuple[str, str]]]]] = {
    "python": [
        ("line comment", "n = 1  # note", [("num", "1"), ("com", "# note")]),
        ("slash star is not a comment", "/* x */ n", []),
        ("escaped quote", 's = "a\\"b"', [("str", '"a\\"b"')]),
        ("escaped backslash does not end the string", 's = "ends \\\\"', [("str", '"ends \\\\"')]),
        ("triple quoted", 's = """a " b\nc"""', [("str", '"""a " b\nc"""')]),
        ("number", "n = 0x1f + 3.5e2 + 1_000", [("num", "0x1f"), ("num", "3.5e2"), ("num", "1_000")]),
        ("keywords", "if x: pass", [("kw", "if"), ("kw", "pass")]),
        ("reserved literals", "v = None or True", [("bi", "None"), ("kw", "or"), ("bi", "True")]),
    ],
    "javascript": [
        ("line comment", "n = 1; // note", [("num", "1"), ("com", "// note")]),
        ("block comment", "/* a */ n", [("com", "/* a */")]),
        ("escaped quote", 's = "a\\"b";', [("str", '"a\\"b"')]),
        ("template literal holds a nested string", 's = `${a ? "x" : "y"}`;', [("str", '`${a ? "x" : "y"}`')]),
        ("number", "n = 0x1f + 3.5e2 + 10n;", [("num", "0x1f"), ("num", "3.5e2"), ("num", "10n")]),
        ("keywords", "return null;", [("kw", "return"), ("kw", "null")]),
        ("builtins", "console.log(undefined);", [("bi", "console"), ("bi", "undefined")]),
    ],
    "typescript": [
        ("line comment", "n = 1; // note", [("num", "1"), ("com", "// note")]),
        ("escaped quote", 's = "a\\"b";', [("str", '"a\\"b"')]),
        ("number", "n = 1_000;", [("num", "1_000")]),
        ("type keywords", "type A = string;", [("kw", "type"), ("kw", "string")]),
        ("reserved literals", "const x = null;", [("kw", "const"), ("kw", "null")]),
    ],
    "rust": [
        ("line comment", "n = 1; // note", [("num", "1"), ("com", "// note")]),
        ("block comment", "/* a */ n", [("com", "/* a */")]),
        ("escaped quote", 'let s = "a\\"b";', [("kw", "let"), ("str", '"a\\"b"')]),
        ("escaped backslash does not end the string", 'let s = "ends \\\\";', [("kw", "let"), ("str", '"ends \\\\"')]),
        ("escaped quote in a character", "let c = '\\'';", [("kw", "let"), ("str", "'\\''")]),
        ("number", "let n = 42u32;", [("kw", "let"), ("num", "42u32")]),
        ("keywords", "fn main() {}", [("kw", "fn")]),
        ("reserved literals", "if ok { true } else { false }", [("kw", "if"), ("kw", "true"), ("kw", "else"), ("kw", "false")]),
        ("variants are builtins", "let v = Some(1);", [("kw", "let"), ("bi", "Some"), ("num", "1")]),
        ("a lifetime is not a character", "fn f<'a>(x: &'a ()) {}", [("kw", "fn")]),
    ],
    "go": [
        ("line comment", "n := 1 // note", [("num", "1"), ("com", "// note")]),
        ("block comment", "/* a */ n", [("com", "/* a */")]),
        ("escaped quote", 's := "a\\"b"', [("str", '"a\\"b"')]),
        ("raw string keeps a backslash", "s := `a\\\"b`", [("str", '`a\\"b`')]),
        ("number", "n := 0x1f + 42", [("num", "0x1f"), ("num", "42")]),
        ("keywords", "func main() {}", [("kw", "func")]),
        ("predeclared", "var s string = nil", [("kw", "var"), ("bi", "string"), ("bi", "nil")]),
        ("capitalised type name", "func f() String {}", [("kw", "func"), ("bi", "String")]),
    ],
    # JSON has no keywords and no comments in valid JSON; the comment rows here
    # are the tolerance the contract allows, and the reserved words are the
    # only words JSON has.
    "json": [
        ("tolerant line comment", '{"a": 1} // note', [("str", '"a"'), ("num", "1"), ("com", "// note")]),
        ("tolerant block comment", '/* a */ {"a": 1}', [("com", "/* a */"), ("str", '"a"'), ("num", "1")]),
        ("escaped quote", '{"a": "b\\"c"}', [("str", '"a"'), ("str", '"b\\"c"')]),
        ("a brace inside a string", '{"a": "} {"}', [("str", '"a"'), ("str", '"} {"')]),
        ("number", '{"a": 1, "b": 2.5e3}', [("str", '"a"'), ("num", "1"), ("str", '"b"'), ("num", "2.5e3")]),
        ("reserved literals", '{"a": true, "b": null}', [("str", '"a"'), ("bi", "true"), ("str", '"b"'), ("bi", "null")]),
    ],
    # YAML has no keywords either.  A key has no class of its own -- there is
    # no name for it in the page's stylesheet -- so it stays plain text.
    "yaml": [
        ("line comment", "a: 1 # note", [("num", "1"), ("com", "# note")]),
        ("a hash inside a scalar is not a comment", "url: http://x#frag", []),
        ("escaped quote", 'k: "a\\"b"', [("str", '"a\\"b"')]),
        ("a colon inside a string", 'k: "not: a mapping"', [("str", '"not: a mapping"')]),
        ("number", "n: 42", [("num", "42")]),
        ("reserved literals", "b: yes\nc: ~", [("bi", "yes"), ("bi", "~")]),
        ("a key is plain text", "name: value", []),
    ],
    "shell": [
        ("line comment", "# note", [("com", "# note")]),
        ("shebang is a comment", "#!/bin/sh", [("com", "#!/bin/sh")]),
        ("escaped quote", 'echo "a\\"b"', [("bi", "echo"), ("str", '"a\\"b"')]),
        ("a backslash in single quotes is literal", "echo 'a\\b'", [("bi", "echo"), ("str", "'a\\b'")]),
        ("the other quote does not end a string", "echo '\"x\"'", [("bi", "echo"), ("str", "'\"x\"'")]),
        ("command substitution", "echo `date`", [("bi", "echo"), ("str", "`date`")]),
        ("number", "sleep 30", [("num", "30")]),
        ("keywords", "if [ -f x ]; then :; fi", [("kw", "if"), ("kw", "then"), ("kw", "fi")]),
        ("builtins", "cd /tmp && echo ok", [("bi", "cd"), ("bi", "echo")]),
        ("a variable is left as plain text", "echo $HOME ${X}", [("bi", "echo")]),
    ],
    "sql": [
        ("line comment", "SELECT 1 -- note", [("kw", "SELECT"), ("num", "1"), ("com", "-- note")]),
        ("block comment", "/* a */ SELECT 1", [("com", "/* a */"), ("kw", "SELECT"), ("num", "1")]),
        ("a doubled quote is one escaped quote", "SELECT 'it''s'", [("kw", "SELECT"), ("str", "'it''s'")]),
        ("a comment marker inside a string", "SELECT 'a--b'", [("kw", "SELECT"), ("str", "'a--b'")]),
        ("number", "SELECT 2.5e3", [("kw", "SELECT"), ("num", "2.5e3")]),
        ("keywords are case-insensitive", "select * from t", [("kw", "select"), ("kw", "from")]),
        ("reserved literals", "WHERE a = true", [("kw", "WHERE"), ("bi", "true")]),
    ],
}


class SafeFragment(unittest.TestCase):
    """The invariant every output has to keep, whatever the language."""

    def assertIntact(self, source: str, html: str, message: str = "") -> None:
        """The source, escaped and wrapped, and nothing else.

        Two ways to fail, both pinned: taking the spans back off the output and
        un-escaping the remainder has to reproduce the source character for
        character, and every `<` and `>` in the output has to belong to a span
        tag this module wrote.  The second is the escape-then-wrap ordering:
        source markup cannot survive inside a token, only inside its class.
        """
        self.assertEqual(unescape("".join(text for _, text in parts(html))), source, message)
        opened = html.count('<span class="tok-')
        self.assertEqual(html.count("<"), opened + html.count("</span>"), message)
        self.assertEqual(html.count(">"), opened + html.count("</span>"), message)
        for kind, text in parts(html):
            if kind is not None:
                self.assertIn(kind, CLASSES, message)


class EveryLanguage(SafeFragment):
    """One method per language, so a failure names the language."""


def _language_test(language: str, fragments: list) -> object:
    def test(self: EveryLanguage) -> None:
        for label, source, expected in fragments:
            with self.subTest(fragment=label):
                html = highlight.highlight(language, source)
                self.assertEqual(tokens(html), expected)
                self.assertIntact(source, html, label)

    test.__doc__ = f"the fragments {language} has to get right, exactly"
    return test


for _language, _fragments in FRAGMENTS.items():
    setattr(EveryLanguage, f"test_{_language}", _language_test(_language, _fragments))


class Escaping(SafeFragment):
    def test_script_payload_is_fully_escaped(self):
        for language, source in MIXED.items():
            with self.subTest(language=language):
                html = highlight.highlight(language, source)
                self.assertNotIn("<script", html)
                self.assertNotIn("</script", html)
                self.assertIn("&lt;script&gt;", html)
                self.assertIntact(source, html)

    def test_a_token_cannot_carry_markup_out_of_its_span(self):
        source = 's = "</span><script>alert(1)</script>";'
        for language in MIXED:
            with self.subTest(language=language):
                html = highlight.highlight(language, source)
                self.assertIntact(source, html)
                # The only closing tag in the output closes a span we wrote.
                self.assertEqual(html.count("</span>"), len(tokens(html)))

    def test_plain_text_is_returned_without_a_wrapper(self):
        html = highlight.highlight("python", "x = y")
        self.assertEqual(html, "x = y")
        self.assertNotIn("<span", html)
        self.assertNotIn("<pre", html)
        self.assertNotIn("<code", html)
        self.assertNotIn("<div", html)

    def test_only_the_page_class_names_are_emitted(self):
        for language, source in MIXED.items():
            with self.subTest(language=language):
                kinds = {kind for kind, _ in tokens(highlight.highlight(language, source))}
                self.assertTrue(kinds)
                self.assertTrue(kinds <= CLASSES, kinds)

    def test_ampersand_is_escaped_before_anything_else(self):
        self.assertEqual(highlight.highlight("unknown", "a & b"), "a &amp; b")
        self.assertEqual(
            highlight.highlight("python", 'x = "a & b"'),
            'x = <span class="tok-str">"a &amp; b"</span>',
        )


class LanguageHint(SafeFragment):
    def test_alias_resolves_to_its_language(self):
        for language, aliases in ALIASES.items():
            for alias in aliases:
                with self.subTest(alias=alias):
                    html = highlight.highlight(alias, MIXED[language])
                    self.assertEqual(html, highlight.highlight(language, MIXED[language]))
                    self.assertTrue(tokens(html), "an alias must not fall back to plain text")
                    self.assertIntact(MIXED[language], html)

    def test_aliases_of_different_languages_stay_different(self):
        for one, two, language in (
            ("py", "js", "javascript"),
            ("rs", "go", "go"),
            ("yml", "json", "json"),
            ("sh", "sql", "sql"),
            ("ts", "js", "typescript"),
        ):
            with self.subTest(pair=(one, two)):
                self.assertNotEqual(
                    highlight.highlight(one, MIXED[language]),
                    highlight.highlight(two, MIXED[language]),
                )

    def test_unknown_language_is_escaped_with_no_spans(self):
        source = "if x < 3:  # <script>alert(1)</script>\n"
        for hint in UNSUPPORTED + UNHIGHLIGHTED:
            with self.subTest(hint=hint):
                html = highlight.highlight(hint, source)
                self.assertEqual(html, escape(source))
                self.assertNotIn("<span", html)
                self.assertIntact(source, html)

    def test_trailing_junk_on_the_hint_is_ignored(self):
        for hint in ("js", "js title='x'", "  js  {1,3}", "JS", "js linenums=5", "js."):
            with self.subTest(hint=hint):
                self.assertEqual(
                    highlight.highlight(hint, MIXED["javascript"]),
                    highlight.highlight("javascript", MIXED["javascript"]),
                )
        self.assertEqual(
            highlight.highlight("py linenums=1 title='x'", MIXED["python"]),
            highlight.highlight("python", MIXED["python"]),
        )

    def test_empty_hint_is_not_a_language(self):
        self.assertEqual(highlight.highlight("", "n = 1"), "n = 1")


class Termination(SafeFragment):
    """An unterminated construct has one exit: it runs to the end of the input."""

    def test_unterminated_block_comment_runs_to_the_end(self):
        for language in ("javascript", "typescript", "rust", "go", "json", "sql"):
            source = "n = 1\n/* open\nnever closed"
            with self.subTest(language=language):
                html = highlight.highlight(language, source)
                self.assertEqual(tokens(html)[-1], ("com", "/* open\nnever closed"))
                self.assertIntact(source, html)

    def test_unterminated_string_runs_to_the_end(self):
        cases = {
            "python": ("s = 'open", "'open"),
            "python triple": ("s = '''open", "'''open"),
            "javascript": ("s = 'open", "'open"),
            "rust": ('s = "open', '"open'),
            "go": ("s := `open", "`open"),
            "json": ('{"a": "open', '"open'),
            "yaml": ('k: "open', '"open'),
            "shell": ("echo 'open", "'open"),
            "sql": ("SELECT 'open", "'open"),
        }
        for label, (source, literal) in cases.items():
            with self.subTest(fragment=label):
                html = highlight.highlight(label.split(" ")[0], source)
                self.assertEqual(tokens(html)[-1], ("str", literal))
                self.assertIntact(source, html)

    def test_a_trailing_backslash_still_terminates(self):
        source = 's = "open\\'
        html = highlight.highlight("python", source)
        self.assertEqual(tokens(html), [("str", '"open\\')])
        self.assertIntact(source, html)

    def test_a_bare_open_delimiter_terminates(self):
        # A delimiter with nothing to close it is one token and the scan ends:
        # the opener is already the whole comment, the whole string.
        for language, source, kind in (
            ("go", "/*", "com"),
            ("go", '"', "str"),
            ("go", "`", "str"),
            ("sql", "'", "str"),
            ("shell", "'", "str"),
            ("python", '"', "str"),
        ):
            with self.subTest(language=language, source=source):
                html = highlight.highlight(language, source)
                self.assertEqual(tokens(html), [(kind, source)])
                self.assertIntact(source, html)


class Empty(SafeFragment):
    def test_empty_source_is_an_empty_fragment(self):
        for language in list(MIXED) + list(UNSUPPORTED) + ["text", "bogus", ""]:
            with self.subTest(language=language):
                self.assertEqual(highlight.highlight(language, ""), "")

    def test_whitespace_only_source_is_unchanged(self):
        for language in MIXED:
            with self.subTest(language=language):
                self.assertEqual(highlight.highlight(language, " \n\t"), " \n\t")


class Determinism(SafeFragment):
    def test_same_input_gives_the_same_output(self):
        for language, source in MIXED.items():
            with self.subTest(language=language):
                first = highlight.highlight(language, source)
                self.assertEqual(first, highlight.highlight(language, source))
                self.assertEqual(first, highlight.highlight(language, source))

    def test_a_repeated_language_does_not_reuse_an_earlier_fragment(self):
        highlight.highlight("python", "n = 1; // c\n")
        self.assertEqual(
            highlight.highlight("python", "n = 2; // c\n"),
            highlight.highlight("python", "n = 2; // c\n"),
        )
        self.assertNotEqual(
            highlight.highlight("python", "n = 1; // c\n"),
            highlight.highlight("python", "n = 2; // c\n"),
        )
        self.assertNotEqual(
            highlight.highlight("python", "n = 1; // c\n"),
            highlight.highlight("javascript", "n = 1; // c\n"),
        )

    def test_nothing_leaks_between_calls(self):
        for language, source in MIXED.items():
            alone = highlight.highlight(language, source)
            for other, other_source in MIXED.items():
                highlight.highlight(other, other_source)
            with self.subTest(language=language):
                self.assertEqual(alone, highlight.highlight(language, source))


class NeverRaises(SafeFragment):
    def test_malformed_arguments_render_escaped_text(self):
        # A hint that is not a string is no hint; a source that is not a string
        # is no source.  Neither may raise, and neither may be guessed at.
        for hint in (None, 7, b"python", ["python"]):
            with self.subTest(hint=hint):
                self.assertEqual(highlight.highlight(hint, "x < y"), "x &lt; y")
        for code in (None, 12, b"x = 1", ["x"]):
            with self.subTest(code=code):
                self.assertEqual(highlight.highlight("python", code), "")

    def test_odd_but_legal_source_never_raises(self):
        for language in MIXED:
            for source in ("\x00\x01", "a\r\nb", " ", "\U0001f600()", "\\", "'''", "0x", "1e", "_"):
                with self.subTest(language=language, source=source):
                    html = highlight.highlight(language, source)
                    self.assertIntact(source, html)

    def test_a_pathological_source_is_still_just_one_pass(self):
        # Every delimiter that could swallow the rest of the text, thousands of
        # times over.  The scan never backtracks, so a fragment this size is
        # work measured in milliseconds and the whole tail is one token.
        source = "/*\n\"'\\`" * 5000
        for language in MIXED:
            with self.subTest(language=language):
                started = time.perf_counter()
                html = highlight.highlight(language, source)
                self.assertLess(time.perf_counter() - started, 5.0)
                self.assertIntact(source, html)


if __name__ == "__main__":
    unittest.main()
