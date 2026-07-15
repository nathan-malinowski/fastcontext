from fastcontext.agent.utils import get_final_answer

_REAL_FILE = __file__


def _wrap(body: str) -> str:
    return f"<final_answer>\n{body}\n</final_answer>"


def test_single_citation_no_explanation():
    text = _wrap(f"{_REAL_FILE}:1")
    result = get_final_answer(text)
    assert f"{_REAL_FILE}:1" in result
    print(result)


def test_single_citation_with_line_range():
    text = _wrap(f"{_REAL_FILE}:1-5")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1-5" in result


def test_multiple_citations():
    text = _wrap(f"{_REAL_FILE}:1-3 (first)\n" f"{_REAL_FILE}:5 (second)")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1-3 (first)" in result
    assert f"{_REAL_FILE}:5 (second)" in result


def test_surrounding_text_is_ignored():
    text = f"some preamble\n{_wrap(f'{_REAL_FILE}:1')}\nsome postamble"
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1" in result
    assert "preamble" not in result
    assert "postamble" not in result


def test_blank_lines_inside_tags_are_skipped():
    text = _wrap(f"\n\n{_REAL_FILE}:1\n\n")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1" in result


def test_mix_valid_and_invalid_files():
    text = _wrap(f"{_REAL_FILE}:1 (kept)\n" "/nonexistent/file.py:2 (dropped)")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1 (kept)" in result
    assert "/nonexistent/file.py" not in result


def test_l_prefixed_line_range():
    text = _wrap(f"{_REAL_FILE}:L1-L5 — parses citations")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1-5 — parses citations" in result


def test_bullet_entry_with_l_prefix():
    text = _wrap(f"- {_REAL_FILE}:L2 — note")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:2 — note" in result


def test_markdown_wrapped_path():
    text = _wrap(f"- **`{_REAL_FILE}`**:L1-L3 — note")
    result = get_final_answer(text)
    print(result)
    assert f"{_REAL_FILE}:1-3 — note" in result


def test_prose_answer_falls_back_to_raw_block():
    body = f"- **Validation location**: `{_REAL_FILE}` — checks ripgrep via shutil.which"
    text = _wrap(body)
    result = get_final_answer(text)
    print(result)
    assert body in result, "unparseable answers must be returned verbatim, not dropped"


def test_all_citations_invalid_falls_back_to_raw_block():
    body = "/nonexistent/file.py:2 (dropped by validation)"
    text = _wrap(body)
    result = get_final_answer(text)
    print(result)
    assert body in result


def test_no_final_answer_tag_returns_text():
    result = get_final_answer("plain answer with no tags")
    print(result)
    assert result == "plain answer with no tags"


if __name__ == "__main__":
    test_single_citation_no_explanation()
    test_single_citation_with_line_range()
    test_multiple_citations()
    test_surrounding_text_is_ignored()
    test_blank_lines_inside_tags_are_skipped()
    test_mix_valid_and_invalid_files()
