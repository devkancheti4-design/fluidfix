# poison_kill.py -- TEACHER C: an ACCIDENTAL kind collision.
# The team's second dictionary file was written by someone who read the
# walkthrough ("pick the lowest free user kind - 4") but counted from 1,
# and landed on kind 3.  Kind 3 is the shipped `flipped-additive` class.
def _noop(line, o):
    return [line]

register(3, "team-todo-marker", "a line carrying a TODO the team tracks",
         re.compile(r"TODO"), _noop)
