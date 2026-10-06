"""Generate a dependency-free PDF from the dashboard gap report."""
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "DASHBOARD_NOT_IMPLEMENTED.md"
OUTPUT = ROOT / "docs" / "DASHBOARD_NOT_IMPLEMENTED.pdf"


def ascii_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def lines_from_markdown(text: str):
    result = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            result.append("")
            continue
        if line.startswith("|---") or line.startswith("|---"):
            continue
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            result.append(" | ".join(cells))
        else:
            line = re.sub(r"^#+\s*", "", line)
            line = re.sub(r"^[-*]\s+", "- ", line)
            result.append(line)
    return result


def wrap(line: str, width: int = 102):
    if not line:
        return [""]
    words = line.split()
    output, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            output.append(current)
            current = word
        else:
            current = word if not current else current + " " + word
    if current:
        output.append(current)
    return output


def build_pdf(lines):
    page_w, page_h = 595, 842
    margin_x, top, bottom, leading = 42, 800, 42, 13
    pages, page = [], []
    y = top
    for source_line in lines:
        for line in wrap(source_line):
            if y < bottom:
                pages.append(page)
                page, y = [], top
            page.append((margin_x, y, line))
            y -= leading
    if page or not pages:
        pages.append(page)

    objects = []
    def add(obj):
        objects.append(obj)
        return len(objects)

    font_id = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []
    for page_lines in pages:
        commands = ["BT", "/F1 9 Tf"]
        for x, y_pos, text in page_lines:
            commands.append(f"1 0 0 1 {x} {y_pos} Tm ({ascii_text(text)}) Tj")
        commands.append("ET")
        content = "\n".join(commands).encode("latin-1")
        content_ids.append(add(f"<< /Length {len(content)} >>\nstream\n" + content.decode("latin-1") + "\nendstream"))
    pages_id = add("PLACEHOLDER")
    for content_id in content_ids:
        page_ids.append(add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_w} {page_h}] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"))
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>"
    catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj.encode("latin-1"))
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)


def main():
    OUTPUT.write_bytes(build_pdf(lines_from_markdown(SOURCE.read_text(encoding="utf-8"))))
    print(OUTPUT)


if __name__ == "__main__":
    main()
