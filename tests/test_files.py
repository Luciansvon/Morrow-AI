"""Pengujian Kontrak Penerimaan AC-007, AC-008, AC-009, AC-018: Pemrosesan Berkas & Routing Lampiran."""


import pytest

from src.files.intake import file_intake
from src.files.parsers.xlsx import spreadsheet_parser


@pytest.mark.asyncio
async def test_ac007_xlsx_and_csv_structural_parsing(tmp_path):
    """AC-007: Spreadsheet diparsing langsung menggunakan parser lokal."""
    # Buat file CSV contoh
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("Bulan,Penjualan,Target\nJanuari,100,80\nFebruari,150,120\n", encoding="utf-8")

    text, data = spreadsheet_parser.parse_csv(str(csv_file))
    assert text is not None
    assert "Januari | 100 | 80" in text
    assert data is not None
    assert len(data["default"]) == 3


@pytest.mark.asyncio
async def test_ac009_unsupported_file_handling(tmp_path):
    """AC-009: Berkas format tidak didukung (misal .exe) ditandai tidak didukung tanpa crash."""
    content = b"MZ\x90\x00\x03\x00\x00\x00"
    att = await file_intake.process_incoming_file("malicious.exe", content)
    assert att.is_supported is False
    assert att.original_name == "malicious.exe"


@pytest.mark.asyncio
async def test_ac018_image_file_intake(tmp_path):
    """AC-018: Berkas gambar (PNG/JPG) didukung dan masuk ke pipeline multimodal."""
    import io

    from PIL import Image

    # Buat gambar PNG valid
    img = Image.new("RGB", (100, 100), color="blue")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_bytes = img_byte_arr.getvalue()

    att = await file_intake.process_incoming_file("poster.png", img_bytes)
    assert att.is_supported is True
    assert "image/png" in att.detected_mime
