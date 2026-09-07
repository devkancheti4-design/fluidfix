def steps_to_zero(n):
    """Count the unit steps needed to walk n down to zero."""
    steps = 0
    while n > 0:
        n -= 2
        steps += 1
    return steps
