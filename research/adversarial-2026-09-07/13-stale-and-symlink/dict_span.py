# A taught class whose repair is a TWO-LINE SpanEdit (the documented
# CHANGE_GRANULARITY shape). Nothing here weakens fluidfix: it is a normal
# user dictionary in the reserved kind slots 4..7.
register(
    4, "accumulator-sign",
    "an accumulator assigned with the wrong sign and then returned negated",
    re.compile(r"^\s*t = a [-+] b\s*$"),
    lambda line, obs: [SpanEdit(obs.lineno, obs.lineno + 1,
                                "    t = a + b\n    return t")],
)
