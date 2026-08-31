#!/usr/bin/env python3
"""Import and run every script and module, so a broken file cannot reach the repo.

    python3 smoke.py

Cheap insurance: render_coupon.py was pushed in a state that would not even parse,
because nothing checked it. This does not test geometry -- verify.py does that -- it
only proves every file imports and every entry point is callable.
"""
import ast
import glob
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def check(label, fn):
    try:
        fn()
        print(f"  ok    {label}")
    except Exception as e:
        FAILS.append(label)
        print(f"  FAIL  {label}: {type(e).__name__}: {e}")


def main():
    sys.path.insert(0, HERE)
    files = sorted(glob.glob(os.path.join(HERE, "*.py"))
                   + glob.glob(os.path.join(HERE, "*", "*.py")))

    print("[parse] every file is syntactically valid")
    for f in files:
        rel = os.path.relpath(f, HERE)
        check(rel, lambda f=f: ast.parse(open(f).read()))

    print("\n[import] every module imports")
    for f in files:
        rel = os.path.relpath(f, HERE)
        if os.path.basename(f) in ("smoke.py",):
            continue
        mod = rel[:-3].replace(os.sep, ".")
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        check(mod, lambda m=mod: importlib.import_module(m))

    print("\n[entry points] every script exposes what it claims")
    import build, verify, plates, render, render_coupon
    for mod, name in ((build, "main"), (verify, "check_fits"), (plates, "main"),
                      (render, "main"), (render_coupon, "main")):
        check(f"{mod.__name__}.{name}", lambda m=mod, n=name: getattr(m, n))

    print(f"\n{len(FAILS)} failures")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
