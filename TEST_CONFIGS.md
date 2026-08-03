# Lake test configurations — 9 runs, in execution order

Each protocol gets 3 configs: baseline, best guess, and one variation on the
best guess. See `EXPERIMENTAL_FLAGS.md` for what each flag does and why.

**Prerequisites:** all bUEs on the `exp-flags-tub-test` branch (`lake_tests`,
`uac-networking`, and for `one_way` roles also `osu_testing`), `bue.service`
restarted after any pull. Run `Baseline` first for each protocol regardless
of what else you skip — it's your reference point for that day's actual
channel/boat conditions.

---

## one_way — `sf` / `cf` / `bw` / `exp_guard_symbol`

All four fields are plain `ui_args` today, no plumbing needed.

### 1. Baseline
| field | value |
|---|---|
| sf (rx + tx) | 8 |
| cf (rx + tx) | 12000 |
| bw (rx + tx) | 6000 |
| exp_guard_symbol (tx) | False |

### 2. Best guess — stacks both validated positives
| field | value |
|---|---|
| sf (rx + tx) | 10 |
| cf (rx + tx) | 12000 |
| bw (rx + tx) | 6000 |
| exp_guard_symbol (tx) | True |

*Orthogonal mechanisms (tail-corruption fix vs. mid-transmission decode
robustness) — safe to combine even though never tested stacked.*

### 3. Variation — push the SF ceiling
| field | value |
|---|---|
| sf (rx + tx) | 11 |
| cf (rx + tx) | 12000 |
| bw (rx + tx) | 6000 |
| exp_guard_symbol (tx) | True |

*SF11 showed the strongest replay-tested recovery (+9 net vs SF9) despite
4x airtime — worth confirming it's actually better than SF10 in the field,
not just in replay.*

---

## vbf — `exp_long_preamble` / `exp_sf`

Assign one `source`, one `sink`, and any number of `node` (relay) roles.
Set the *same* values on every `source`/`node` in a given run unless the
config says otherwise.

### 4. Baseline
| field | value |
|---|---|
| exp_long_preamble (source + all nodes) | False |
| exp_sf (source + all nodes) | 9 |

### 5. Best guess — directly validated (31–44% recovery on real strong-signal failures)
| field | value |
|---|---|
| exp_long_preamble (source + all nodes) | True |
| exp_sf (source + all nodes) | 9 |

### 6. Variation — untested stack, timing-checked safe
| field | value |
|---|---|
| exp_long_preamble (source + all nodes) | True |
| exp_sf (source + all nodes) | 10 |

*Never validated stacked (long_preamble and SF both act on the same
DETECT-margin mechanism, unlike one_way's orthogonal pair). Time-on-air
checked: ≈6.8s, still fits inside VBF's 10s periodic send interval.*
**Do not go to SF11 here** — long_preamble+SF11 ≈13.6s, longer than the
send interval itself, which breaks VBF's periodic timing model outright,
not just costs airtime.

---

## fp_group — `exp_sf`

Assign one `coordinator`, rest `worker`. Requires the frame_sync buffer fix
(`chirp_engine.py`, commit `c4704d9`) — confirmed on this branch; without it,
SF9+ silently breaks every worker's ability to *receive* replies (their own
transmissions still go out, so it looks like a link problem, not a crash).

### 7. Baseline
| field | value |
|---|---|
| exp_sf (coordinator + all workers) | 8 |

### 8. Best guess
| field | value |
|---|---|
| exp_sf (coordinator + all workers) | 10 |

*Live-validated on real water (2026-08-03): confirmed real REQ→CON exchange
completes correctly at SF10 after the buffer fix.*

### 9. Variation — push the ceiling
| field | value |
|---|---|
| exp_sf (coordinator + all workers) | 11 |

*fp_group doesn't have VBF's fixed-interval problem (its send loop waits
out each message's actual duration, not a fixed period) — SF11 just costs
throughput here, not correctness. Bigger caveat than the other two
protocols: the SF-vs-performance data behind this recommendation was built
entirely from VBF traffic at 12kHz — fp_group runs across 5 different
channels (12–44kHz), so this is a wider extrapolation than the `one_way` or
`vbf` recommendations.*
