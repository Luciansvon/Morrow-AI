"""Pengujian Kontrak Penerimaan AC-021: Event Deduplication."""

import pytest

from src.core.normalizer import MessageNormalizer


@pytest.mark.asyncio
async def test_ac021_duplicate_event_detected():
    """AC-021: Event ID yang sama ditolak saat dikirim kedua kalinya."""
    event_id = "evt_unique_12345"

    # Pengiriman pertama -> Bukan duplikat
    is_dup_1 = await MessageNormalizer.is_duplicate_event(event_id, platform="telegram")
    assert is_dup_1 is False

    # Pengiriman ulang (redelivery) -> Terdeteksi DUPLIKAT
    is_dup_2 = await MessageNormalizer.is_duplicate_event(event_id, platform="telegram")
    assert is_dup_2 is True
