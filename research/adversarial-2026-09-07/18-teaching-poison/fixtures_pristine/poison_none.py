# poison_none.py -- TEACHER E: an applier that returns None (docs: "never None").
register(4, "returns-none", "any return line", re.compile(r"return"),
         lambda line, o: None)
