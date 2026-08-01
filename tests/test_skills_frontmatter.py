from __future__ import annotations

from skills.frontmatter import parse_skill_doc


def test_parse_valid_frontmatter() -> None:
    text = '---\nname: foo\ndescription: "does things"\n---\n\n# Body\n'
    meta, body = parse_skill_doc(text)
    assert meta == {"name": "foo", "description": "does things"}
    assert body == "# Body\n"


def test_parse_crlf_line_endings() -> None:
    text = '---\r\nname: foo\r\ndescription: bar\r\n---\r\n\r\nbody\r\n'
    meta, body = parse_skill_doc(text)
    assert meta == {"name": "foo", "description": "bar"}
    assert body == "body\r\n"


def test_parse_no_frontmatter_returns_whole_text_as_body() -> None:
    text = "# plain markdown, no frontmatter"
    meta, body = parse_skill_doc(text)
    assert meta == {}
    assert body == text


def test_parse_broken_yaml_degrades_to_empty_meta() -> None:
    text = "---\nname: [unclosed\n---\n\nbody"
    meta, body = parse_skill_doc(text)
    assert meta == {}
    assert body == "body"


def test_parse_missing_closing_delimiter_degrades() -> None:
    text = "---\nname: foo\nno closing delimiter here"
    meta, body = parse_skill_doc(text)
    assert meta == {}
    assert body == text


def test_parse_non_dict_yaml_degrades_to_empty_meta() -> None:
    text = "---\n- just\n- a\n- list\n---\n\nbody"
    meta, body = parse_skill_doc(text)
    assert meta == {}
    assert body == "body"


def test_parse_empty_file() -> None:
    meta, body = parse_skill_doc("")
    assert meta == {}
    assert body == ""
