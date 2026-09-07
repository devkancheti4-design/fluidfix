"""26-router-exhaustive: one single-token fixture per shipped fault kind.
Shared by live_trace.py and cost.py so both build identical trees."""

FIXTURES = {
    # name: (module source with ONE token wrong, failing test source)
    # one fixture per shipped fault kind, so every route the body can
    # produce is exercised end to end.
    "k0_strictness": (
        "def count_above(xs, t):\n    n = 0\n    for x in xs:\n"
        "        if x >= t:\n            n = n + 1\n    return n\n",
        "from mod import count_above\n\n"
        "def test_it():\n    assert count_above([1, 5, 5, 9], 5) == 1\n"),
    "k1_literal_off_by_one": (
        "def secs(days):\n    return days * 3601\n",
        "from mod import secs\n\ndef test_it():\n    assert secs(2) == 7200\n"),
    "k2_swapped_return": (
        "def ratio(a, b):\n    return a // b\n",
        "from mod import ratio\n\ndef test_it():\n    assert ratio(2, 9) == 4\n"),
    "k3_flipped_additive": (
        "def net(a, b):\n    return a + b\n",
        "from mod import net\n\ndef test_it():\n    assert net(7, 2) == 5\n"),
    "k8_minmax_swap": (
        "def cap(a, b):\n    return min(a, b)\n",
        "from mod import cap\n\ndef test_it():\n    assert cap(3, 8) == 8\n"),
    "k9_flipped_augmented": (
        "def drain(n, k):\n    for _ in range(k):\n        n += 1\n    return n\n",
        "from mod import drain\n\ndef test_it():\n    assert drain(10, 3) == 7\n"),
    "k10_flipped_comparison": (
        "def bigger(a, b):\n    if a < b:\n        return a\n    return b\n",
        "from mod import bigger\n\ndef test_it():\n    assert bigger(3, 8) == 8\n"),
    "k11_reversed_minus": (
        "def gap(a, b):\n    d = a - b\n    return d\n",
        "from mod import gap\n\ndef test_it():\n    assert gap(2, 9) == 7\n"),
    "k12_flipped_boolean": (
        "DEBUG = True\n\n\ndef mode():\n"
        "    return 'debug' if DEBUG else 'prod'\n",
        "from mod import mode\n\ndef test_it():\n    assert mode() == 'prod'\n"),
    # outside the vocabulary: the loop must refuse, and we see which routes
    # it burned on the way
    "out_of_vocab": (
        "def both(a, b):\n    return a and b\n",
        "from mod import both\n\ndef test_it():\n    assert both(1, 0) == 1\n"),
}
