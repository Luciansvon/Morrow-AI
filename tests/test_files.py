"""File parsing and intake regression tests."""


import pytest

from src.files.intake import file_intake
from src.files.parsers.xlsx import spreadsheet_parser


@pytest.mark.asyncio
async def test_csv_structural_parsing(tmp_path):
    """CSV diparsing langsung menggunakan parser lokal."""
    # Buat file CSV contoh
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text("Bulan,Penjualan,Target\nJanuari,100,80\nFebruari,150,120\n", encoding="utf-8")

    text, data = spreadsheet_parser.parse_csv(str(csv_file))
    assert text is not None
    assert "Januari | 100 | 80" in text
    assert data is not None
    assert len(data["default"]) == 3


@pytest.mark.asyncio
async def test_unsupported_file_handling(tmp_path):
    """Format tidak didukung ditolak tanpa crash."""
    content = b"MZ\x90\x00\x03\x00\x00\x00"
    att = await file_intake.process_incoming_file("malicious.exe", content)
    assert att.is_supported is False
    assert att.original_name == "malicious.exe"


@pytest.mark.asyncio
async def test_image_file_intake(tmp_path):
    """PNG valid diterima oleh intake."""
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
