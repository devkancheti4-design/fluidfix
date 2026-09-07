def ordinal_number(n):
    if n >= 10:          # defect: should be n > 10
        return "th"
    return "st"
