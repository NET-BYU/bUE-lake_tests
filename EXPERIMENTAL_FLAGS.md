# Experimental flags

Registry of `exp_*` toggles across all three protocols (`one_way`, `vbf`, `fp_group`).
There's no shared code between `osu_testing` and `uac-networking` (separate repos,
separate deploy paths), so this file is the single place that lists what exists
across both -- the actual mechanism in each protocol is just a normal `ui_args`
entry in `utw_config.yaml`, same as `msg`/`sf`/`per`/etc.

## Convention

- Every experimental toggle is named `exp_<thing>`, always appended at the *end*
  of a role's `ui_args` list (never inserted earlier) -- `ui_args` values are
  matched to CLI flags **positionally** by `utw.py`, so inserting one in the
  middle would silently break every other value after it.
- Default is always the value that reproduces today's exact production behavior
  (usually `false`). Nothing changes for a test unless the flag is explicitly set.
- Each protocol's own entrypoint script re-declares the matching argparse flag
  and threads it down into its flowgraph class -- there is intentionally no
  shared Python import for this, to avoid a cross-repo dependency that doesn't
  exist anywhere else in this codebase today.
- A flag that changes the on-air signal (TX/protocol structure) can only be
  validated on the lake, not by replaying old recordings -- RX-only fixes
  (frame_sync, header_decoder, etc.) don't need a flag at all, they get proven
  via pristine-vs-fixed replay and merged straight to the gr-lora_sdr main
  branch once confirmed.
- If a flag's implementation ever needs new DSP logic inside a gr-lora_sdr C++
  block (not just different data flowing into the existing pipeline), that
  requires a recompile of `libgnuradio-lora_sdr.so` and cannot be a pure-Python
  toggle -- see the "TX code sites" note below before assuming a flag is a
  one-file Python change.

## Active flags

| Flag | Protocol / role | Default | What it does |
|---|---|---|---|
| `exp_guard_symbol` | `one_way` / `tx` | `false` | Appends one throwaway trailing byte to the outgoing message (`osu_testing/tx.py`, `_GuardSymbolAppender`) so the transducer's end-of-transmission ring-down corrupts that byte instead of the last real payload/CRC byte. Pure Python/message-level change -- no gr-lora_sdr recompile. See the 2026-07-08 major->buford tail-corruption investigation for the root-cause evidence. |
| `exp_long_preamble` | `vbf` / `source`, `node` | `false` | Sends 16 preamble upchirp symbols instead of the default 8 (`audio_comms/chirp_engine_single.py`). Gives frame_sync's DETECT state more chances to catch a clean consecutive-match run despite real symbol-to-symbol bin jitter (measured 7-9 bins on candace->linda, exceeding the ±1 margin), using frame_sync's existing `additional_upchirps` tolerance (already handles a longer-than-configured TX preamble) -- zero RX-side changes. `preamble_len` was already a constructor parameter on both `modulate_impl.cc` and `frame_sync_impl.cc`, just not threaded through the Python wrapper layers (`lora_sdr_lora_tx.py`) or up to `Chirp_Engine`/`Node`/`Source` -- exactly the "expose as a constructor param" pattern flagged below. Also fixed `get_tx_duration()`, which had `n_preamble_sym` hardcoded independent of the actual configured value -- left unfixed, enabling this flag would have silently reproduced the same source_periodic timing bug found earlier this investigation (see [[project_frame_sync_fix]]). Costs ~0.68s more airtime per message at SF9. |

## Note: when a flag needs a gr-lora_sdr recompile instead

Most experimental TX ideas (like the guard symbol) can be implemented by changing
*what bytes flow into* the existing, unmodified gr-lora_sdr pipeline -- no C++
changes, no rebuild. But if a future idea requires new behavior *inside* a block
(e.g. tuning `frame_sync_impl.cc`'s hardcoded SFO correction threshold, or
changing `modulate_impl.cc`'s padding/amplitude logic), that block has to be
touched and `libgnuradio-lora_sdr.so` rebuilt (`make && sudo make install` in
`gr-lora_sdr/build/`). Whether that ever becomes flag-switchable at runtime
(rather than requiring two separately-built installs, swapped by hand like we
did during investigation) depends on whether the tunable piece gets exposed as
a block constructor parameter (e.g. `frame_zero_padd` already is) -- that's a
one-time, small C++ change worth doing proactively for anything we expect to
want to A/B test on the lake. Keep this in mind before assuming a TX-side idea
is a quick Python-only change -- check whether it needs a new source block
parameter first.
