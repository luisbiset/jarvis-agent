#!/usr/bin/env python3
"""Normalize legacy mojibake in repository text files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".toml", ".json", ".py", ".sh", ".mjs", ".yaml", ".yml", ".txt", ".css"}
BAD = {chr(0xC2), chr(0xC3), chr(0xE2), chr(0xEF), chr(0xFFFD)}

def repair_piece(piece: str) -> str:
    current = piece
    replacements = {
        chr(0xC3) + chr(0xA3): chr(0xE3),
        chr(0xC3) + chr(0xA7): chr(0xE7),
        chr(0xC3) + chr(0xA9): chr(0xE9),
        chr(0xC3) + chr(0xA7): chr(0xE7),
        chr(0xC3) + chr(0xA1): chr(0xE1),
        chr(0xC3) + chr(0xB3): chr(0xF3),
        chr(0xC3) + chr(0xAD): chr(0xED),
        chr(0xC3) + chr(0xBA): chr(0xFA),
        chr(0xC3) + chr(0xB5): chr(0xF5),
        chr(0xC3) + chr(0xA0): chr(0xE0),
        chr(0xE2) + chr(0x20AC) + chr(0x153): chr(0x201C),
        chr(0xE2) + chr(0x20AC) + chr(0x157): chr(0x201D),
        chr(0xE2) + chr(0x20AC) + chr(0x147): chr(0x2013),
    }
    for source, target in replacements.items():
        current = current.replace(source, target)
    for _ in range(3):
        if not any(char in BAD for char in current):
            break
        try:
            candidate = current.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                candidate = current.encode("latin1").decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                break
        if candidate == current:
            break
        current = candidate
    return current

def repair(text: str) -> str:
    bom = text[:1] if text.startswith(chr(0xFEFF)) else ""
    body = text[1:] if bom else text
    output = []
    for line in body.splitlines(keepends=True):
        parts, buffer = [], []
        for char in line:
            if ord(char) <= 255 or char in {chr(0x20AC), chr(0x152), chr(0x153), chr(0x178)}:
                buffer.append(char)
            else:
                if buffer:
                    parts.append(repair_piece("".join(buffer))); buffer = []
                parts.append(char)
        if buffer:
            parts.append(repair_piece("".join(buffer)))
        output.append("".join(parts))
    return bom + "".join(output)

def main() -> int:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in {".git", ".aghuse-assistant", "__pycache__", "target", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        fixed = repair(text)
        if fixed != text:
            path.write_text(fixed, encoding="utf-8", newline="")
            changed += 1
    print(f"UTF8_NORMALIZED={changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
