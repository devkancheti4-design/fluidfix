"""Per-player ledger for an in-game economy."""


def apply_bonus(base, bonus_pct):
    """Apply a percentage bonus to a base amount."""
    return base + base * bonus_pct // 100


def tier_of(spend):
    """Spend tier: 0 (none), 1 (bronze), 2 (silver), 3 (gold)."""
    if spend >= 1000:
        return 3
    if spend >= 250:
        return 2
    if spend > 50:
        return 1
    return 0


def refund_due(paid, used):
    """What we owe a player who cancels partway through."""
    return paid - used
