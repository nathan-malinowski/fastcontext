import os
import re
from pathlib import Path


FINAL_ANSWER_RE = re.compile(r"<final_answer>(.*?)</final_answer>", re.DOTALL)

# /absolute/path/to/file_1.py:10-15 (explanation 1)
# /absolute/path/to/file_1.py:10 (explanation 2)
# - path/to/file.py:L10-L15 — explanation 3
# - **`path/to/file.py`**:L10 — explanation 4
# The range must be contiguous (no spaces around the dash): a spaced hyphen
# after the start line is explanation text, not an end line.
CITATION_ENTRY_RE = re.compile(r"(.+?):L?(\d+)(?:[-–]L?(\d+))?\s*(.*)")


def load_system_prompt() -> str:
    return (Path(__file__).parent / "system.md").read_text(encoding="utf-8").strip()


def parse_citations(text: str) -> list[dict]:
    final_answer = FINAL_ANSWER_RE.search(text)
    if final_answer is None:
        return []

    entries = final_answer.group(1).strip().splitlines()

    entries = [e for e in entries if e.strip()]

    citations = []
    for entry in entries:
        entry = re.sub(r"^\s*[-*]+\s*", "", entry.strip())
        match = CITATION_ENTRY_RE.match(entry)
        if match:
            file_path = match.group(1).strip().strip("*`").strip()
            explanation = match.group(4).strip() if match.group(4) else ""
            start_line = int(match.group(2))
            end_line = int(match.group(3)) if match.group(3) else start_line
            line_range = f"{start_line}-{end_line}" if end_line != start_line else str(start_line)
            citations.append(
                {
                    "path": file_path,
                    "line_range": line_range,
                    "start_line": start_line,
                    "end_line": end_line,
                    "explanation": explanation,
                }
            )
    return citations


def validate_citations(citations: list[dict], work_dir: str | None = None) -> list[dict]:
    """Keep citations whose path exists; relative paths resolve against work_dir."""
    validated = []
    for c in citations:
        path = c["path"]
        if not os.path.isabs(path) and work_dir:
            path = os.path.join(work_dir, path)
        if os.path.isfile(path):
            validated.append(c)
    return validated


def format_citations(citations: list, validate: bool = True, work_dir: str | None = None) -> str:

    if validate:
        citations = validate_citations(citations, work_dir)

    formatted = []
    for c in citations:
        if c["explanation"]:
            formatted.append(f"{c['path']}:{c['line_range']} {c['explanation']}")
        else:
            formatted.append(f"{c['path']}:{c['line_range']}")
    return "<final_answer>\n" + "\n".join(formatted) + "\n</final_answer>"


def get_final_answer(text: str | None, work_dir: str | None = None) -> str:
    if not text:
        return ""
    final_answer = FINAL_ANSWER_RE.search(text)
    if final_answer is None:
        return text.strip()
    citations = parse_citations(text)
    validated = validate_citations(citations, work_dir)
    if validated:
        return format_citations(validated, validate=False)
    if citations:
        # Citations parsed but none exist on disk: keep the empty block as an
        # explicit failure signal instead of passing hallucinated paths through.
        return "<final_answer>\n\n</final_answer>"
    # Prose-only answer with no parseable citations — return it verbatim.
    return "<final_answer>\n" + final_answer.group(1).strip() + "\n</final_answer>"


if __name__ == "__main__":
    print(load_system_prompt())
