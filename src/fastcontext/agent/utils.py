import os
import re
from pathlib import Path


def load_system_prompt() -> str:
    return (Path(__file__).parent / "system.md").read_text(encoding="utf-8").strip()


def parse_citations(text: str) -> list:
    final_answer = re.search(r"<final_answer>(.*?)</final_answer>", text, re.DOTALL)
    if final_answer is None:
        return {"final_answer": text.strip(), "citations": []}

    entries = final_answer.group(1).strip().splitlines()

    entries = [e for e in entries if e.strip()]

    citations = []
    for entry in entries:
        # /absolute/path/to/file_1.py:10-15
        # /absolute/path/to/file_1.py:10-15 (explanation 1)
        # /absolute/path/to/file_1.py:10 (explanation 2)
        # - path/to/file.py:L10-L15 — explanation 3
        # - **`path/to/file.py`**:L10 — explanation 4
        entry = re.sub(r"^\s*[-*]+\s*", "", entry.strip())
        match = re.match(r"(.+?):L?(\d+)(?:\s*[-–]\s*L?(\d+))?\s*(.*)", entry)
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


def format_citations(citations: list, validate: bool = True) -> str:

    if validate:
        validated_citations = []
        for c in citations:
            # if not file or not existing, skip this citation
            if not os.path.isfile(c["path"]):
                continue
            validated_citations.append(c)

        citations = validated_citations

    formatted = []
    for c in citations:
        if c["explanation"]:
            formatted.append(f"{c['path']}:{c['line_range']} {c['explanation']}")
        else:
            formatted.append(f"{c['path']}:{c['line_range']}")
    return "<final_answer>\n" + "\n".join(formatted) + "\n</final_answer>"


def get_final_answer(text: str) -> str:
    final_answer = re.search(r"<final_answer>(.*?)</final_answer>", text, re.DOTALL)
    if final_answer is None:
        return text.strip()
    citations = parse_citations(text)
    formatted = format_citations(citations)
    if not re.search(r"<final_answer>\s*</final_answer>", formatted):
        return formatted
    # No citation survived parsing/validation — return the raw answer verbatim
    # rather than an empty block.
    return "<final_answer>\n" + final_answer.group(1).strip() + "\n</final_answer>"


if __name__ == "__main__":
    print(load_system_prompt())
