# Diagon Alley book nook

A parametric illuminated book nook — a narrow crooked wizarding shopping lane,
**8 × 10.5 × 12 in**, with forced perspective, hidden LED wiring and a removable outer
brick skin for access.

| | |
|---|---|
| Printer rules | [`../README.md`](../README.md) — **read it first**, everything in it applies here |
| The live document | [`PLAN.md`](PLAN.md) — architecture, decisions, research register |
| Phases | [`SPEC.md`](SPEC.md) — and the exit test for each |

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe checks.py -v
```

## Files

| | |
|---|---|
| [`params.py`](params.py) | every dimension, with its provenance |
| [`checks.py`](checks.py) | the check suite — registry-driven, printer-aware |
| [`joints.py`](joints.py) | the D-pin and its socket, tested by real insertion |
| [`coupon.py`](coupon.py) · [`plate.py`](plate.py) | the test plate, and the Bambu project writer |
| [`ingest.py`](ingest.py) | read settings back out of a saved Bambu project |
| [`preflight.py`](preflight.py) | predicts the slicer's sharp-tail and cantilever warnings. Minutes per plate — too slow to gate on, so opening the file in Bambu is still the review step |
| [`archive/`](archive/) | two previous attempts — the record, **not** the starting point |

## History

Two attempts were made at building it as a 182-part kit; both ended with a bench of parts
that would not go together. The reasons are written down rather than forgotten:

- [`07_RETROSPECTIVE.md`](archive/docs/07_RETROSPECTIVE.md)
- [`08_JOINT_DESIGN.md`](archive/docs/08_JOINT_DESIGN.md)
- [`09_COUPON_RESULTS.md`](archive/docs/09_COUPON_RESULTS.md)

Most of what those attempts cost has since been promoted into
[`../README.md`](../README.md), because it applies to anything printed on this machine —
the 0.30 mm fit clearance, the internal corner radius, the text stroke floor and the
0.72 em advance all came out of this project's wasted plates.

**`params.py` is the authority; this file is the human summary.** Where they disagree, the
code wins — it is the one that can fail a build.
