"""Model catalog OpenRouter. Harga di sini hanya fallback estimate; billing aktual memakai usage.cost bila tersedia."""

from typing import NamedTuple


class ModelSpec(NamedTuple):
    model_id: str
    name: str
    input_price_1m: float
    output_price_1m: float
    cached_input_price_1m: float | None
    context_window: int
    is_multimodal: bool
    supports_reasoning: bool


MODEL_CATALOG: dict[str, ModelSpec] = {
    "deepseek_v4_flash": ModelSpec(
        model_id="deepseek/deepseek-v4-flash",
        name="DeepSeek V4 Flash",
        input_price_1m=0.09,
        output_price_1m=0.18,
        cached_input_price_1m=None,
        context_window=1_000_000,
        is_multimodal=False,
        supports_reasoning=True,
    ),
    "mimo_v2_5": ModelSpec(
        model_id="xiaomi/mimo-v2.5",
        name="MiMo-V2.5",
        input_price_1m=0.14,
        output_price_1m=0.28,
        cached_input_price_1m=None,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
    "minimax_m3": ModelSpec(
        model_id="minimax/minimax-m3",
        name="MiniMax M3",
        input_price_1m=0.30,
        output_price_1m=1.20,
        cached_input_price_1m=0.06,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
    "deepseek_v4_pro": ModelSpec(
        model_id="deepseek/deepseek-v4-pro",
        name="DeepSeek V4 Pro",
        input_price_1m=0.435,
        output_price_1m=0.87,
        cached_input_price_1m=None,
        context_window=1_000_000,
        is_multimodal=False,
        supports_reasoning=True,
    ),
    "gpt_5_6_luna": ModelSpec(
        model_id="openai/gpt-5.6-luna",
        name="GPT-5.6 Luna",
        input_price_1m=1.00,
        output_price_1m=6.00,
        cached_input_price_1m=None,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
    "claude_sonnet_5": ModelSpec(
        model_id="anthropic/claude-sonnet-5",
        name="Claude Sonnet 5",
        input_price_1m=2.00,
        output_price_1m=10.00,
        cached_input_price_1m=None,
        context_window=1_000_000,
        is_multimodal=True,
        supports_reasoning=True,
    ),
}
