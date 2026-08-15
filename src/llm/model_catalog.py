"""Katalog model resmi OpenRouter untuk Morrow v0.2 (Audit 15 Agustus 2026)."""

from typing import NamedTuple


class ModelSpec(NamedTuple):
    model_id: str
    name: str
    input_price_1m: float
    output_price_1m: float
    context_window: int
    is_multimodal: bool
    supports_reasoning: bool


# Katalog Model Pilihan
MODEL_CATALOG: dict[str, ModelSpec] = {
    "deepseek_v4_flash": ModelSpec(
        model_id="deepseek/deepseek-v4-flash-0731",
        name="DeepSeek V4 Flash 0731",
        input_price_1m=0.14,
        output_price_1m=0.28,
        context_window=1_000_000,
        is_multimodal=False,
        supports_reasoning=True,
    ),
    "mimo_v2_5": ModelSpec(
        model_id="xiaomi/mimo-v2.5",
        name="MiMo-V2.5",
        input_price_1m=0.14,
        output_price_1m=0.28,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
    "minimax_m3": ModelSpec(
        model_id="minimax/minimax-m3",
        name="MiniMax M3",
        input_price_1m=0.30,
        output_price_1m=1.20,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=False,
    ),
    "deepseek_v4_pro": ModelSpec(
        model_id="deepseek/deepseek-v4-pro-0813",
        name="DeepSeek V4 Pro 0813",
        input_price_1m=1.32,
        output_price_1m=3.96,
        context_window=1_000_000,
        is_multimodal=False,
        supports_reasoning=True,
    ),
    "gpt_5_6_luna": ModelSpec(
        model_id="openai/gpt-5.6-luna-pro",
        name="GPT-5.6 Luna Pro",
        input_price_1m=0.50,
        output_price_1m=3.00,
        context_window=200_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
    "claude_sonnet_5": ModelSpec(
        model_id="anthropic/claude-sonnet-5",
        name="Claude Sonnet 5",
        input_price_1m=2.00,
        output_price_1m=10.00,
        context_window=200_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
}
