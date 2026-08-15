"""Parser dokumen Spreadsheet (Excel XLSX dan CSV) secara struktural."""

import csv
from typing import Any


class SpreadsheetParser:
    """Parser untuk mengekstrak data tabel dari XLSX dan CSV."""

    @staticmethod
    def parse_xlsx(file_path: str) -> tuple[str | None, dict[str, Any] | None]:
        """Membaca seluruh lembar kerja (*sheets*) dan baris dari berkas .xlsx."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            structured_data = {}
            text_lines = []

            for sheetname in wb.sheetnames:
                sheet = wb[sheetname]
                rows_data = []
                for row in sheet.iter_rows(values_only=True):
                    # Filter baris yang seluruh isinya None
                    if any(cell is not None for cell in row):
                        str_row = [str(c) if c is not None else "" for c in row]
                        rows_data.append(str_row)
                        text_lines.append(" | ".join(str_row))

                structured_data[sheetname] = rows_data

            summary_text = f"=== Spreadsheet XLSX (Total Sheets: {len(wb.sheetnames)}) ===\n" + "\n".join(text_lines[:100]) # Batasi 100 baris awal untuk ringkasan teks
            return summary_text, structured_data
        except Exception as e:
            return f"Error parsing XLSX: {e!s}", None

    @staticmethod
    def parse_csv(file_path: str) -> tuple[str | None, dict[str, Any] | None]:
        """Membaca berkas CSV."""
        try:
            rows = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        rows.append(row)

            text_lines = [" | ".join(r) for r in rows[:100]]
            summary_text = f"=== File CSV (Total Rows: {len(rows)}) ===\n" + "\n".join(text_lines)
            return summary_text, {"default": rows}
        except Exception as e:
            return f"Error parsing CSV: {e!s}", None


spreadsheet_parser = SpreadsheetParser()
