from dataclasses import dataclass


@dataclass(frozen=True)
class CapitalTier:
    name: str
    min_equity: float
    max_equity: float | None
    max_positions: int
    risk_per_trade: float
    description: str


TIERS = [
    CapitalTier("micro", 0, 500, 1, 0.03, "$0–$500: Micro account"),
    CapitalTier("small", 500, 2_000, 2, 0.02, "$500–$2K: Small account"),
    CapitalTier("medium", 2_000, 5_000, 3, 0.02, "$2K–$5K: Medium account"),
    CapitalTier("large", 5_000, 10_000, 4, 0.02, "$5K–$10K: Large account"),
    CapitalTier("xlarge", 10_000, 25_000, 5, 0.015, "$10K–$25K: XLarge account"),
    CapitalTier("day_trader", 25_000, None, 6, 0.01, "$25K+: Day trader unlocked"),
]


def get_tier_for_equity(equity: float) -> CapitalTier:
    for tier in TIERS:
        if tier.max_equity is None:
            if equity >= tier.min_equity:
                return tier
        elif tier.min_equity <= equity < tier.max_equity:
            return tier
    return TIERS[0]


def get_tier_config(equity: float) -> dict:
    tier = get_tier_for_equity(equity)
    return {
        "tier": tier.name,
        "max_positions": tier.max_positions,
        "risk_per_trade": tier.risk_per_trade,
        "description": tier.description,
        "min_equity": tier.min_equity,
        "max_equity": tier.max_equity,
    }
