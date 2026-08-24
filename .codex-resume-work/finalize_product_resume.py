from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import os
import tempfile


REFERENCE = Path(r"D:\company_agent\.codex-resume-work\source.docx")
DRAFT = Path(r"D:\company_agent\.codex-resume-work\product-final.docx")
OUTPUT = Path(r"C:\Users\lenovo\Desktop\董星晨\董星晨的个人简历_产品方向版.docx")
EDITABLE_PARTS = {"word/document.xml", "word/footer1.xml"}


with ZipFile(DRAFT, "r") as draft_zip:
    replacements = {name: draft_zip.read(name) for name in EDITABLE_PARTS}

fd, temp_name = tempfile.mkstemp(suffix=".docx", dir=OUTPUT.parent)
os.close(fd)
temp_path = Path(temp_name)

try:
    with ZipFile(REFERENCE, "r") as source_zip, ZipFile(
        temp_path, "w", compression=ZIP_DEFLATED
    ) as output_zip:
        for info in source_zip.infolist():
            data = replacements.get(info.filename, source_zip.read(info.filename))
            copied_info = ZipInfo(info.filename, date_time=info.date_time)
            copied_info.compress_type = info.compress_type
            copied_info.comment = info.comment
            copied_info.extra = info.extra
            copied_info.internal_attr = info.internal_attr
            copied_info.external_attr = info.external_attr
            copied_info.create_system = info.create_system
            copied_info.flag_bits = info.flag_bits
            output_zip.writestr(copied_info, data)

    os.replace(temp_path, OUTPUT)
finally:
    if temp_path.exists():
        temp_path.unlink()

print(OUTPUT)
