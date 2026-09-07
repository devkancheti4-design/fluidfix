"""How much of the churn _SKIP fails to exclude: vendored trees and demos."""
import collections
import re
import sys
sys.path.insert(0, "/Users/kanchetidevieswar/neo/fluidfix/src")
from fluidfix.hotspots import bugfix_churn  # noqa: E402

NOT_ENGINE = re.compile(
    r"(^|/)(glfw|glad|imgui|freetype|glew|stb|jsmn|simde|enkiTS|HelloWorld|"
    r"Testbed|Contributions|Building)(/|$|\.)", re.I)
churn, sc, fx = bugfix_churn(sys.argv[1])
total = sum(churn.values())
bad = collections.Counter({f: n for f, n in churn.items()
                           if NOT_ENGINE.search(f)})
print(f"churn: {len(churn)} files / {total} touches")
print(f"vendored-or-demo that _SKIP missed: {len(bad)} files / "
      f"{sum(bad.values())} touches ({sum(bad.values())/total:.1%})")
for f, n in bad.most_common(10):
    print(f"  {n:4d}  {f}")
top57 = [f for f, _ in churn.most_common(57)]
print(f"inside the 57-file '60%' set: "
      f"{sum(1 for f in top57 if NOT_ENGINE.search(f))} such files")
