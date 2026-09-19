import json, difflib

ORIG = {}
ORIG["gemma3:4b-hard/backoff"] = '''def backoff(attempts, base):
    """The delay before each retry, doubling each time and starting at `base`.
    One entry per attempt."""
    if attempts == 0:
        return base
    elif attempts == 1:
        return base * 2
    elif attempts == 2:
        return base * 4
    elif attempts == 3:
        return base * 8
    else:
        return base * (2 ** (attempts - 3))
'''

ORIG["qwen3.5:4b-hard/trim_to_fit"] = '''def trim_to_fit(words, width):
    """Take words from the front while the joined line stays within `width` characters,
    counting the single spaces between them."""
    result = []
    current_length = 0

    for word in words:
        if not word:
            continue

        # Calculate length if we add a space before this word (if it's not the first)
        potential_length = current_length + 1 + len(word)

        # If adding this word exceeds the width, stop
        if potential_length > width:
            break

        result.append(word)
        current_length += 1 + len(word)

    return ' '.join(result)
'''

TESTS = {}
TESTS["gemma3:4b-hard/backoff"] = '''
assert backoff(3, 1) == [1,2,4]
assert backoff(1, 2) == [2]
assert backoff(0, 1) == []
'''
TESTS["qwen3.5:4b-hard/trim_to_fit"] = '''
assert trim_to_fit(['ab','cd'], 5) == ['ab','cd']
assert trim_to_fit(['ab','cd'], 4) == ['ab']
assert trim_to_fit(['abc'], 2) == []
'''

# ---------------- LEVEL 2: additions only ----------------
L2 = {}
L2["gemma3:4b-hard/backoff"] = '''def backoff(attempts, base):
    """The delay before each retry, doubling each time and starting at `base`.
    One entry per attempt."""
    return [base * (2 ** i) for i in range(attempts)]
    if attempts == 0:
        return base
    elif attempts == 1:
        return base * 2
    elif attempts == 2:
        return base * 4
    elif attempts == 3:
        return base * 8
    else:
        return base * (2 ** (attempts - 3))
'''

L2["qwen3.5:4b-hard/trim_to_fit"] = '''def trim_to_fit(words, width):
    """Take words from the front while the joined line stays within `width` characters,
    counting the single spaces between them."""
    kept = []
    for w in words:
        if len(' '.join(kept + [w])) > width:
            break
        kept.append(w)
    return kept
    result = []
    current_length = 0

    for word in words:
        if not word:
            continue

        # Calculate length if we add a space before this word (if it's not the first)
        potential_length = current_length + 1 + len(word)

        # If adding this word exceeds the width, stop
        if potential_length > width:
            break

        result.append(word)
        current_length += 1 + len(word)

    return ' '.join(result)
'''

# ---------------- LEVEL 3: free rewrite ----------------
L3 = {}
L3["gemma3:4b-hard/backoff"] = '''def backoff(attempts, base):
    """The delay before each retry, doubling each time and starting at `base`.
    One entry per attempt."""
    return [base * (2 ** i) for i in range(attempts)]
'''

L3["qwen3.5:4b-hard/trim_to_fit"] = '''def trim_to_fit(words, width):
    """Take words from the front while the joined line stays within `width` characters,
    counting the single spaces between them."""
    result = []
    current_length = 0

    for word in words:
        # length of the joined line if this word is appended
        potential_length = current_length + len(word) + (1 if result else 0)

        if potential_length > width:
            break

        result.append(word)
        current_length = potential_length

    return result
'''

def check_additions_only(orig, new):
    """True iff `new` is `orig` with lines added only (no line changed/deleted)."""
    o = orig.splitlines()
    n = new.splitlines()
    sm = difflib.SequenceMatcher(None, o, n, autojunk=False)
    bad = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            bad.append((tag, o[i1:i2], n[j1:j2]))
    return (not bad), bad

def run(src, tests):
    ns = {}
    exec(compile(src, "<patch>", "exec"), ns)
    exec(compile(tests, "<tests>", "exec"), ns)

ok = True
for level, table in (("level2", L2), ("level3", L3)):
    for cid, src in table.items():
        if src == "IMPOSSIBLE":
            print(f"{level} {cid}: declared IMPOSSIBLE")
            continue
        if level == "level2":
            clean, bad = check_additions_only(ORIG[cid], src)
            print(f"{level} {cid}: additions-only = {clean}")
            if not clean:
                ok = False
                for b in bad:
                    print("   VIOLATION:", b)
        try:
            run(src, TESTS[cid])
            print(f"{level} {cid}: TESTS PASS")
        except Exception as e:
            ok = False
            print(f"{level} {cid}: TESTS FAIL -> {type(e).__name__}: {e}")

print("\nALL OK" if ok else "\nPROBLEMS FOUND")

if ok:
    out = {"level2": L2, "level3": L3}
    path = "/private/tmp/claude-501/-Users-kanchetidevieswar-neo/7c20050a-238d-4391-b3a1-e4cb0be69061/scratchpad/answers_l23.payload.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    print("payload written:", path)
