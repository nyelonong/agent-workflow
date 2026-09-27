from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import markdown_doc  # noqa: E402  (the renderer lives in scripts/ and is not a package)

KINDS = {"blank", "heading", "code", "quote", "list", "table", "rule", "text"}
EMITTED_TAGS = {"b", "i", "code", "s"}

# One document that exercises every construct at once, used by the invariant
# test: a comment on "line 42" is only meaningful if every source line is here.
KITCHEN_SINK = "\n".join(
    [
        "# Reviewer spec",  # 1
        "",  # 2
        "Body with **bold**, *italic*, ~~strike~~ and `code`.",  # 3
        "A [link](https://example.com/x?a=1&b=2) and a bare <script>alert(1)</script>.",  # 4
        "",  # 5
        "## Rules",  # 6
        "",  # 7
        "- top level",  # 8
        "  - nested item",  # 9
        "- [ ] unchecked task",  # 10
        "- [x] checked task",  # 11
        "1. ordered",  # 12
        "",  # 13
        "| column | other |",  # 14
        "|---|---|",  # 15
        "| a | b |",  # 16
        "",  # 17
        "> quoted **line**",  # 18
        "",  # 19
        "---",  # 20
        "",  # 21
        "```python",  # 22
        "value = 1",  # 23
        "",  # 24  a blank line inside a fence is still code
        "**not bold**",  # 25
        "```",  # 26
        "",  # 27
        "Trailing prose with `a * b * c` inside a code span.",  # 28
    ]
)


def source_lines(text: str) -> list[str]:
    """The line count the reviewer must agree with: split on newlines, and a
    trailing newline terminates the last line rather than starting a new one."""
    if text == "":
        return []
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


class LineInvariant(unittest.TestCase):
    def assert_invariant(self, text: str) -> list[dict]:
        produced = markdown_doc.rows(text)
        expected = source_lines(text)
        self.assertEqual(
            len(produced),
            len(expected),
            f"row count {len(produced)} != source line count {len(expected)}",
        )
        for index, row in enumerate(produced):
            self.assertEqual(row["n"], index + 1)
            self.assertIn(row["kind"], KINDS)
            self.assertIsInstance(row["html"], str)
            self.assertEqual(("level" in row), row["kind"] == "heading")
            self.assertFalse(row["kind"] != "list" and "checked" in row)
        return produced

    def test_every_construct_at_once(self):
        produced = self.assert_invariant(KITCHEN_SINK)
        self.assertEqual(
            [row["kind"] for row in produced],
            [
                "heading", "blank", "text", "text", "blank",
                "heading", "blank", "list", "list", "list", "list", "list",
                "blank", "table", "table", "table", "blank", "quote", "blank",
                "rule", "blank", "code", "code", "code", "code", "code", "blank",
                "text",
            ],
        )
        self.assertEqual(produced[0]["level"], 1)
        self.assertEqual(produced[5]["level"], 2)

    def test_row_content_follows_its_own_line(self):
        produced = markdown_doc.rows(KITCHEN_SINK)
        for number, row in enumerate(produced, start=1):
            line = source_lines(KITCHEN_SINK)[number - 1]
            if row["kind"] == "blank":
                self.assertEqual(row["html"], "")
            if row["kind"] in {"code", "rule"}:
                self.assertNotIn("<b>", row["html"])
                self.assertNotIn("<i>", row["html"])
            if "<script>" in line:  # the payload row stays readable text
                self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", row["html"])
            if "**bold**, *italic*" in line:  # inline formatting is per line
                self.assertIn("<b>bold</b>", row["html"])
                self.assertIn("<i>italic</i>", row["html"])

    def test_single_line_without_trailing_newline(self):
        produced = self.assert_invariant("just one line")
        self.assertEqual(produced[0], {"n": 1, "kind": "text", "text": "just one line", "html": "just one line"})

    def test_trailing_newline_adds_no_row(self):
        self.assert_invariant("one\ntwo\n")
        self.assertEqual(len(markdown_doc.rows("one\ntwo\n")), 2)
        self.assertEqual(markdown_doc.rows("one\ntwo\n"), markdown_doc.rows("one\ntwo"))

    def test_empty_document(self):
        self.assertEqual(markdown_doc.rows(""), [])
        self.assertEqual(markdown_doc.rows(chr(0xFEFF)), [])

    def test_only_a_newline_is_one_blank_line(self):
        self.assertEqual(markdown_doc.rows("\n"), [{"n": 1, "kind": "blank", "text": "", "html": ""}])
        self.assertEqual(
            markdown_doc.rows("\n\n\n"),
            [{"n": n, "kind": "blank", "text": "", "html": ""} for n in (1, 2, 3)],
        )


class FencedCode(unittest.TestCase):
    def test_blank_line_inside_fence_is_code(self):
        produced = markdown_doc.rows("```\nfirst\n\nthird\n```\nafter")
        self.assertEqual([row["kind"] for row in produced], ["code"] * 5 + ["text"])
        self.assertEqual(produced[2]["n"], 3)
        self.assertEqual(produced[2]["html"], "")  # a blank line inside a fence
        self.assertEqual(produced[-1]["n"], 6)

    def test_unclosed_fence_runs_to_end_of_input(self):
        produced = markdown_doc.rows("intro\n```py\nx = 1\n\n# not a heading\n")
        self.assertEqual([row["kind"] for row in produced], ["text"] + ["code"] * 4)
        self.assertEqual(produced[-1]["n"], 5)

    def test_other_fence_character_does_not_close(self):
        produced = markdown_doc.rows("```\n~~~\nstill code\n```\ntext")
        self.assertEqual([row["kind"] for row in produced], ["code", "code", "code", "code", "text"])

    def test_closing_fence_must_be_at_least_as_long(self):
        produced = markdown_doc.rows("````\n```\n````\ntext")
        self.assertEqual([row["kind"] for row in produced], ["code", "code", "code", "text"])

    def test_code_rows_are_never_emphasised(self):
        html = markdown_doc.rows("```\n**x** and <b>y</b>\n```")[1]["html"]
        self.assertEqual(html, "**x** and &lt;b&gt;y&lt;/b&gt;")


class LineEndings(unittest.TestCase):
    def test_crlf_matches_lf(self):
        self.assertEqual(
            markdown_doc.rows("# h\r\n\r\n- a\r\n"),
            markdown_doc.rows("# h\n\n- a\n"),
        )

    def test_leading_bom_is_dropped(self):
        produced = markdown_doc.rows(chr(0xFEFF) + "# heading\nbody")
        self.assertEqual([row["kind"] for row in produced], ["heading", "text"])
        self.assertEqual(produced[0]["html"], "heading")

    def test_crlf_and_bom_together(self):
        produced = markdown_doc.rows(chr(0xFEFF) + "a\r\nb\r\n")
        self.assertEqual([row["n"] for row in produced], [1, 2])


class Inline(unittest.TestCase):
    def html(self, source: str) -> str:
        return markdown_doc.rows(source)[0]["html"]

    def test_bold_wrapping_a_code_span(self):
        self.assertEqual(
            self.html("a **bold with `code` inside** tail"),
            "a <b>bold with <code>code</code> inside</b> tail",
        )

    def test_asterisks_inside_a_code_span_stay_literal(self):
        self.assertEqual(self.html("run `a * b * c` now"), "run <code>a * b * c</code> now")
        self.assertEqual(self.html("`**not bold**`"), "<code>**not bold**</code>")
        self.assertEqual(self.html("`~~not strike~~`"), "<code>~~not strike~~</code>")

    def test_emphasis_inside_a_code_span_is_not_applied(self):
        self.assertEqual(self.html("`**x**`"), "<code>**x**</code>")

    def test_emphasis_forms(self):
        self.assertEqual(self.html("**b** __b__ *i* _i_ ~~s~~"), "<b>b</b> <b>b</b> <i>i</i> <i>i</i> <s>s</s>")

    def test_underscores_inside_a_word_are_left_alone(self):
        self.assertEqual(self.html("snake_case_name"), "snake_case_name")

    def test_link_keeps_label_and_emits_no_anchor(self):
        html = self.html("see [the spec](https://example.com/a?b=1&c=2) now")
        self.assertEqual(html, "see the spec now")
        self.assertNotIn("<a", html)
        self.assertNotIn("example.com", html)

    def test_link_label_still_takes_emphasis(self):
        self.assertEqual(self.html("[**bold** label](u)"), "<b>bold</b> label")

    def test_bare_brackets_are_literal(self):
        self.assertEqual(self.html("[not a link]"), "[not a link]")


class Escaping(unittest.TestCase):
    def test_script_tag_is_visible_text(self):
        html = markdown_doc.rows("before <script>alert(1)</script> after")[0]["html"]
        self.assertEqual(html, "before &lt;script&gt;alert(1)&lt;/script&gt; after")
        self.assertNotIn("<script", html)

    def test_attribute_injection_cannot_escape_the_cell(self):
        html = markdown_doc.rows('<img src=x onerror="alert(1)">')[0]["html"]
        self.assertEqual(html, '&lt;img src=x onerror="alert(1)"&gt;')

    def test_ampersand_is_escaped_before_its_neighbours(self):
        self.assertEqual(markdown_doc.rows("a & <b> c")[0]["html"], "a &amp; &lt;b&gt; c")

    def test_only_the_declared_tags_are_emitted(self):
        produced = markdown_doc.rows(KITCHEN_SINK)
        for row in produced:
            self.assertLessEqual(set(re.findall(r"</?([a-zA-Z0-9]+)", row["html"])), EMITTED_TAGS, row)


class Blocks(unittest.TestCase):
    def kind(self, source: str) -> str:
        return markdown_doc.rows(source)[0]["kind"]

    def test_thematic_break_is_not_a_list(self):
        for source in ("---", "***", "___", "- - -", "-----"):
            self.assertEqual(self.kind(source), "rule", source)
        self.assertNotIn("checked", markdown_doc.rows("---")[0])

    def test_table_rows_including_the_delimiter(self):
        self.assertEqual(self.kind("| a | b |"), "table")
        self.assertEqual(self.kind("|---|---|"), "table")
        self.assertEqual(self.kind("| --- | :---: |"), "table")
        self.assertEqual(markdown_doc.rows("|---|---|")[0]["html"], "---|---")
        self.assertNotIn("level", markdown_doc.rows("|---|---|")[0])

    def test_task_list_items(self):
        unchecked = markdown_doc.rows("- [ ] write the renderer")[0]
        checked = markdown_doc.rows("- [x] write the renderer")[0]
        upper = markdown_doc.rows("* [X] done")[0]
        for row in (unchecked, checked, upper):
            self.assertEqual(row["kind"], "list")
        self.assertFalse(unchecked["checked"])
        self.assertIn("☐", unchecked["html"])
        self.assertTrue(checked["checked"])
        self.assertTrue(upper["checked"])
        self.assertIn("☑", checked["html"])

    def test_plain_list_item_has_no_checked_key(self):
        self.assertNotIn("checked", markdown_doc.rows("- just a bullet")[0])
        self.assertNotIn("checked", markdown_doc.rows("1. ordered")[0])

    def test_nested_item_is_its_own_row(self):
        produced = markdown_doc.rows("- parent\n  - child\n    - grandchild\nplain")
        self.assertEqual([row["kind"] for row in produced], ["list", "list", "list", "text"])
        self.assertEqual([row["n"] for row in produced], [1, 2, 3, 4])
        self.assertEqual([row["html"] for row in produced[:3]], ["parent", "child", "grandchild"])

    def test_heading_levels_and_trailing_hashes(self):
        self.assertEqual(markdown_doc.rows("### three")[0]["level"], 3)
        self.assertEqual(
            markdown_doc.rows("## closed ##")[0],
            {"n": 1, "kind": "heading", "text": "## closed ##", "level": 2, "html": "closed"},
        )
        self.assertEqual(markdown_doc.rows("###### six")[0]["level"], 6)
        self.assertEqual(markdown_doc.rows("#nospace")[0]["kind"], "text")

    def test_heading_level_is_capped(self):
        self.assertEqual(markdown_doc.rows("####### too deep")[0]["kind"], "text")

    def test_blank_and_text(self):
        self.assertEqual(markdown_doc.rows("   \t ")[0]["kind"], "blank")
        self.assertEqual(markdown_doc.rows("words")[0]["kind"], "text")

    def test_quote_keeps_content_and_drops_the_marker(self):
        produced = markdown_doc.rows("> quoted **line**")
        self.assertEqual(produced[0], {"n": 1, "kind": "quote", "text": "> quoted **line**", "html": "quoted <b>line</b>"})


class MalformedInput(unittest.TestCase):
    def test_never_raises(self):
        for source in ("***", "`", "**", "[](", "[]()", "- [ ]", "|", "||", ">", "#", "\x00\x005\x00", "a`b``c"):
            with self.subTest(source=source):
                produced = markdown_doc.rows(source)
                self.assertEqual(len(produced), len(source_lines(source)))
                for row in produced:
                    self.assertIn(row["kind"], KINDS)

    def test_repeated_calls_are_deterministic(self):
        self.assertEqual(markdown_doc.rows(KITCHEN_SINK), markdown_doc.rows(KITCHEN_SINK))


if __name__ == "__main__":
    unittest.main()


class BlockTests(unittest.TestCase):
    """Blocks carry the source range a comment has to name."""

    KITCHEN_SINK = (
        "# Title\n"
        "\n"
        "first paragraph line\n"
        "still the same paragraph\n"
        "\n"
        "## Design\n"
        "\n"
        "- item one\n"
        "  wrapped onto the next line\n"
        "- item two\n"
        "\n"
        "1. numbered\n"
        "\n"
        "> a quote\n"
        "> still the quote\n"
        "\n"
        "| a | b |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n"
        "\n"
        "```\n"
        "code line\n"
        "\n"
        "still code\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        "last paragraph\n"
    )

    def test_blocks_cover_every_line_exactly_once(self) -> None:
        for text in (self.KITCHEN_SINK, "", "one line", "# only a heading\n", "\n\n\n"):
            with self.subTest(text=text[:20]):
                total = len(text.splitlines())
                covered: list[int] = []
                for block in markdown_doc.blocks(text):
                    covered.extend(range(block["start"], block["end"] + 1))
                self.assertEqual(list(range(1, total + 1)), covered, "blocks must tile the document")

    def test_a_block_range_is_inclusive_and_ordered(self) -> None:
        for block in markdown_doc.blocks(self.KITCHEN_SINK):
            self.assertLessEqual(block["start"], block["end"])
            self.assertGreaterEqual(block["start"], 1)
            self.assertLessEqual(block["end"], len(self.KITCHEN_SINK.splitlines()))

    def test_a_paragraph_is_one_block(self) -> None:
        blocks = [b for b in markdown_doc.blocks(self.KITCHEN_SINK) if b["kind"] == "text"]
        self.assertEqual([(3, 4), (29, 29)], [(b["start"], b["end"]) for b in blocks])

    def test_a_wrapped_list_item_stays_one_block(self) -> None:
        lists = [b for b in markdown_doc.blocks(self.KITCHEN_SINK) if b["kind"] == "list"]
        self.assertEqual([(8, 9), (10, 10), (12, 12)], [(b["start"], b["end"]) for b in lists])
        self.assertIn("wrapped", lists[0]["html"])

    def test_quotes_tables_and_fences_are_single_blocks(self) -> None:
        by_kind: dict[str, list] = {}
        for block in markdown_doc.blocks(self.KITCHEN_SINK):
            by_kind.setdefault(block["kind"], []).append((block["start"], block["end"]))
        self.assertEqual([(14, 15)], by_kind["quote"])
        self.assertEqual([(17, 19)], by_kind["table"])
        self.assertEqual([(21, 25)], by_kind["code"])
        self.assertEqual([(1, 1), (6, 6)], by_kind["heading"])
        self.assertEqual([(27, 27)], by_kind["rule"])

    def test_consecutive_blank_lines_form_one_block(self) -> None:
        blanks = [b for b in markdown_doc.blocks("a\n\n\n\nb\n") if b["kind"] == "blank"]
        self.assertEqual([(2, 4)], [(b["start"], b["end"]) for b in blanks])

    def test_heading_level_and_task_state_reach_the_block(self) -> None:
        blocks = markdown_doc.blocks("## Design\n\n- [x] done\n")
        heading = next(b for b in blocks if b["kind"] == "heading")
        self.assertEqual(2, heading["level"])
        task = next(b for b in blocks if b["kind"] == "list")
        self.assertTrue(task["checked"])

    def test_blocks_are_deterministic(self) -> None:
        first = markdown_doc.blocks(self.KITCHEN_SINK)
        second = markdown_doc.blocks(self.KITCHEN_SINK)
        self.assertEqual(first, second, "the same bytes must produce the same ranges")

    def test_an_empty_document_has_no_blocks(self) -> None:
        self.assertEqual([], markdown_doc.blocks(""))

    def test_a_block_carries_the_html_of_its_lines(self) -> None:
        block = next(b for b in markdown_doc.blocks("a **bold** para\n") if b["kind"] == "text")
        self.assertIn("<b>bold</b>", block["html"])


class RawSourceTests(unittest.TestCase):
    """A block hands a real markdown engine the lines a comment will name."""

    def test_every_row_keeps_its_raw_source_line(self) -> None:
        document = "## Title\n\nA **bold** line\nand a plain one\n\n- item\n\n> quoted\n"
        for row in markdown_doc.rows(document):
            with self.subTest(n=row["n"]):
                self.assertIn("text", row, "a row without its raw line cannot be re-rendered")
        by_number = {row["n"]: row["text"] for row in markdown_doc.rows(document)}
        self.assertEqual("## Title", by_number[1])
        self.assertEqual("A **bold** line", by_number[3])
        self.assertEqual("> quoted", by_number[8])

    def test_a_block_carries_the_source_of_exactly_its_lines(self) -> None:
        document = "intro\n\nfirst\nsecond\n\n## Next\n"
        lines = document.splitlines()
        for block in markdown_doc.blocks(document):
            with self.subTest(kind=block["kind"]):
                expected = lines[block["start"] - 1 : block["end"]]
                self.assertEqual(expected, block["source"].split("\n"))

    def test_a_heading_block_is_its_raw_line(self) -> None:
        block = next(b for b in markdown_doc.blocks("## Goals\n\ntext\n") if b["kind"] == "heading")
        self.assertEqual("## Goals", block["source"])
