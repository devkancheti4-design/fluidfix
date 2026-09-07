# poison_crash.py -- TEACHER D: an applier that raises (docs: "never raise").
def _boom(line, o):
    raise RuntimeError("teacher D has a bug in its transform")

register(4, "explodes", "any line at all", re.compile(r"return"), _boom)
