# Screenshots

These are generated from **demo data**, never from a real instance, and they are
reproducible:

```bash
python3 samples/make_samples.py
ZHT_STATE_DIR=samples/state ZHT_WWW_DIR=samples/state/www \
  python3 zhtimes/report.py --config config.example.json
python3 scripts/make-screenshots.py
```

That rewrites all six PNGs in this folder. Run it after any change to the
dashboard's markup or styling, or the images quietly stop matching the product.

## Why demo data, always

A real dashboard shows the companies you are pursuing, the roles you have applied
to, your compensation target, your stated limits, and the questions you plan to
ask a named recruiter. Published to a public repository, that is permanent,
searchable and attached to your name while you are interviewing — and a
screenshot of your own salary target sitting beside an employer's posted band
gives away a negotiating position for nothing.

The demo renders the identical layout from invented employers, invented postings
and invented sources, all pointing at `example.com`. There is no visual advantage
to using real data and there is a real cost, so the generator only ever reads
`samples/state`.

## What gets produced

| File | Shown in | Contents |
|---|---|---|
| `newspaper.png` | README hero | the front page: counters, stage status, five notices, Help Wanted panel |
| `assessment-eligibility.png` | README gallery | card header, scores, eligibility table, the six-row competency table |
| `assessment-reasoning.png` | README gallery | qualification, transferable experience, preference fit, career direction |
| `assessment-gaps.png` | README gallery | compensation, workload indicators, confirmed gaps vs not documented, recruiter questions |
| `research-company.png` | README gallery | Our Correspondent Reports — company stage and what the role actually does |
| `research-questions.png` | TUTORIAL | published compensation data, ambiguous requirements, questions to ask |

## Requirements

`wkhtmltoimage` is required. `python3-pil` and `pngquant` are optional: without
them the images are produced but are larger and keep some trailing whitespace.

```bash
sudo apt-get install wkhtmltopdf python3-pil pngquant optipng
```

`scripts/screenshot-overrides.css` exists because wkhtmltoimage runs an old Qt
WebKit that predates CSS Grid and modern flex sizing. It restores the layout a
current browser renders, and is used only by the generator — nothing in the
application reads it.

## If you capture by hand instead

Check the image, not the page you think you captured: no real employer name, no
real salary figure, no line of the form "the candidate's stated target of ...",
no browser chrome showing anything personal, and the URL bar reading
`localhost`. The fictional names that *should* appear are Northwind Analytics,
Vance Maritime Group, Halden Instruments, Calder & Roe and Ashgrove Health.
