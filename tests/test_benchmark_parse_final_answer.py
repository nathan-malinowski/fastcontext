import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "benchmark" / "evaluation"))

from utils import parse_final_answer  # noqa: E402


def test_bullet_and_l_prefixed_entry_parses():
    result = parse_final_answer("<final_answer>\n- **`src/x.py`**:L10-L15 — note\n</final_answer>")
    assert result["n_broken_lines"] == 0
    assert result["n_citations"] == 1
    c = result["citations"][0]
    assert c["path"] == "src/x.py"
    assert (c["start_line"], c["end_line"]) == (10, 15)


def test_legacy_absolute_entry_still_parses():
    result = parse_final_answer("<final_answer>\n/abs/file_1.py:10-15 (explanation 1)\n</final_answer>")
    assert result["n_citations"] == 1
    c = result["citations"][0]
    assert c["path"] == "/abs/file_1.py"
    assert (c["start_line"], c["end_line"]) == (10, 15)
    assert result["n_citations_lines"] == 6


def test_spaced_hyphen_does_not_invert_range_metrics():
    result = parse_final_answer("<final_answer>\nsrc/app.py:120 - 3 call sites need updating\n</final_answer>")
    assert result["n_citations"] == 1
    c = result["citations"][0]
    assert (c["start_line"], c["end_line"]) == (120, 120)
    assert result["n_citations_lines"] == 1, "line metrics must never go negative"
