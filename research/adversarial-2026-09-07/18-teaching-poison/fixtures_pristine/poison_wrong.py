# poison_wrong.py -- TEACHER A: a WRONG worked example, written down honestly.
#
# Incident INC-9001. The ticket said "the balance screen showed -3, users
# expect 3". The on-call engineer looked at ONE failing case and wrote the
# incident down as:
#
#     return balance - fee          <- shipped a negative
#     return abs(balance - fee)     <- "the fix"
#
# This is a WRONG worked example. The real class is a reversed subtraction
# (fluidfix ships that class as kind 11, reversed-minus-operands). abs()
# happens to green the one case in the ticket and silently changes the sign
# of EVERY negative result forever after.
#
# Nothing in register() checks whether a worked example is correct.
register(
    4,
    "negative-result-guard",
    "a returned subtraction that can go negative where the caller expects a "
    "magnitude",
    re.compile(r"^\s*(?:return\s|[A-Za-z_]\w*\s=\s).*\s-\s"),
    lambda line, o: (line.replace("return ", "return abs(", 1) + ")"
                     if line.lstrip().startswith("return ")
                     else line.replace(" = ", " = abs(", 1) + ")"),
)
