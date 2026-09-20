"""Cost estimation for escalated crop calls. Always used as a worst-case upper
bound (every flagged photo assumed to need the stronger/pricier tier) before
any paid call runs - see the desktop tool spec's cost-gating requirement."""

# Approximate tokens per escalation call: one downscaled image plus prompt text
# for input, a small JSON crop decision for output. This is a documented
# approximation, not measured - refine against response.usage once the
# escalation step has actually run on real photos.
APPROX_INPUT_TOKENS_PER_CALL = 1700
APPROX_OUTPUT_TOKENS_PER_CALL = 100


def estimate_call_cost(provider, tier: str) -> float:
    input_price, output_price = provider.price_per_million_tokens(tier)
    return (
        (APPROX_INPUT_TOKENS_PER_CALL / 1_000_000) * input_price
        + (APPROX_OUTPUT_TOKENS_PER_CALL / 1_000_000) * output_price
    )


def estimate_worst_case_batch_cost(provider, num_flagged_photos: int) -> float:
    return num_flagged_photos * estimate_call_cost(provider, "strong")
