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
        match = re.match(r"(.+?):(\d+(?:-\d+)?)\s*(.*)", entry.strip())
        if match:
            file_path = match.group(1).strip()
            line_range = match.group(2).strip()
            explanation = match.group(3).strip() if match.group(3) else ""
            start_line, end_line = line_range.split("-") if "-" in line_range else (line_range, line_range)
            start_line = int(start_line.strip())
            end_line = int(end_line.strip())
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
    citations = parse_citations(text)
    final_answer = format_citations(citations)
    return final_answer


if __name__ == "__main__":
    print(load_system_prompt())
