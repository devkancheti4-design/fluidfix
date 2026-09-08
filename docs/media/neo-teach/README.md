# neo-teach.mp4 — how this recording was made

A real terminal running the real tool. Every command in the video executed
live while the recorder was running; the outputs are what fluidfix printed.
Nothing is generated, drawn, or edited afterwards.

Recorder: [VHS 0.11.0](https://github.com/charmbracelet/vhs) (a headless
xterm over ttyd, captured by Chrome, encoded by ffmpeg), 1920x1080,
Catppuccin Mocha, JetBrains Mono. VHS produces MP4 at a fixed 25 fps and
drops frames when a screenshot takes longer than its 40 ms tick, so the
video runs roughly 10% faster than the wall clock during heavy redraws.
Every duration that matters is printed by fluidfix itself on screen
(`repaired line 8 in 6 suite runs (2.3s)`), and those are unaffected.

## Reproduce

```bash
brew install vhs                      # pulls ttyd and ffmpeg
pip install -U fluidfix pytest pytest-cov
./setup.sh /path/to/demo/shipwise     # builds the demo repo + the shipped regression
# edit the `cd` line in neo-teach.tape to that path and your interpreter, then:
vhs neo-teach.tape
```

`setup.sh` creates a three-module shipping-quote service with a pytest
suite, commits it green, then commits one shipped regression (`1 + VAT` ->
`1 - VAT`). Everything else — the zero-teaching repair, the refusal of the
untaught class, the one-example dictionary, the repair, the second file
repaired for free — happens on camera, in that order, and the demo repo's
`git log` at the end is the receipt:

```
fluidfix: restore shipwise/invoice.py:9
invoice: simplify rounding
fluidfix: restore shipwise/quote.py:8
quote: simplify rounding
fluidfix: restore shipwise/invoice.py:8
invoice: tidy the vat formula
shipwise: quotes, invoices, tests
```
