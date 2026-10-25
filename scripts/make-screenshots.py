#!/usr/bin/env python3
"""Render the six README screenshots from the demo dashboard.

    python3 samples/make_samples.py
    ZHT_STATE_DIR=samples/state ZHT_WWW_DIR=samples/state/www \
      python3 zhtimes/report.py --config config.example.json
    python3 scripts/make-screenshots.py

Dev tool, not part of the application: it needs wkhtmltoimage, and optionally
pngquant and python3-pil to trim and compress the result. The application itself
remains stdlib-only with no dependencies.

Screenshots are built from DEMO data, always. A real dashboard shows the
companies you are pursuing, your compensation target and your stated limits;
published to a public repository that is permanent and searchable.

Runs wkhtmltoimage over the demo page. Its engine is old Qt WebKit, which
predates CSS Grid and modern flex sizing, so shotfix.css restores the layout a
real browser produces. Nothing here touches the shipped product: it reads the
rendered demo page and writes PNGs.
"""
import pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
ROOT = HERE.parent
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "samples" / "state" / "www" / "index.html"))
OUT = ROOT / "docs" / "images"
OUT.mkdir(exist_ok=True)
page = SRC.read_text()
fix = (HERE / "screenshot-overrides.css").read_text()

style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)


def shell(html, width):
    return f"""<!doctype html><meta charset="utf-8">
<style>{style}</style><style>{fix}</style>
<style>
  body{{margin:0}}
  .shotwrap{{padding:22px 26px;max-width:{width - 52}px}}
  .shotwrap .copy{{display:block}}
</style>
<body><div class="sheet"><div class="shotwrap">{html}</div></div></body>"""


def render(name, html, width, crop_h=None):
    tmp = OUT / f"_{name}.html"
    tmp.write_text(shell(html, width))
    cmd = ["wkhtmltoimage", "--quiet", "--format", "png", "--width", str(width),
           "--enable-local-file-access", str(tmp), str(OUT / f"{name}.png")]
    if crop_h:
        cmd[2:2] = ["--crop-x", "0", "--crop-y", "0", "--crop-w", str(width),
                    "--crop-h", str(crop_h)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    tmp.unlink()
    return (OUT / f"{name}.png").stat().st_size


# ---- the Northwind card ------------------------------------------------------
card = re.search(r'<details class="ad".*?</details>', page, re.S).group(0)
summary = re.search(r"<summary>.*?</summary>", card, re.S).group(0)
# float must precede the block it sits beside for old WebKit
summary = re.sub(r'(<summary>\s*)(<span class="hl">.*?</span></span>)\s*(<a class="applybtn".*?</a>)',
                 lambda m: m.group(1) + m.group(3) + "\n" + m.group(2), summary, flags=re.S)
copy = re.search(r'<div class="copy">(.*)</div>\s*</details>', card, re.S).group(1)

# split the card body on its own section headings
parts = re.split(r'(?=<h3>)', copy)
lead = parts[0]


def pick(*titles):
    out = []
    for p in parts[1:]:
        h = re.match(r"<h3>(.*?)</h3>", p)
        if h and any(t.lower() in h.group(1).lower() for t in titles):
            out.append(p)
    return "".join(out)


research = pick("Our Correspondent Reports")
cut = research.find("<p><strong>3. PUBLISHED COMPENSATION")
if cut == -1:
    cut = research.find("3. PUBLISHED COMPENSATION")
res_a, res_b = research[:cut], research[cut:]
head = re.match(r"<h3>.*?</h3>", research, re.S).group(0)

SHOTS = [
    ("assessment-eligibility", f'<div class="ad">{summary}</div><div class="copy">'
                               f'{lead}{pick("Eligibility", "Core Competencies")}</div>', 920),
    ("assessment-reasoning", '<div class="copy">' + pick(
        "Qualification", "Transferable Experience", "Preference Fit", "Career Direction")
        + "</div>", 920),
    ("assessment-gaps", '<div class="copy">' + pick(
        "Compensation", "Workload Indicators", "Gaps / Risks", "Recommendation")
        + "</div>", 920),
    ("research-company", f'<div class="copy">{res_a}</div>', 980),
    ("research-questions", f'<div class="copy">{head}{res_b}</div>', 980),
]

def finish(path):
    """Trim the trailing background wkhtmltoimage leaves, then compress."""
    try:
        from PIL import Image, ImageChops
        im = Image.open(path).convert("RGB")
        w, h = im.size
        bg = im.getpixel((w - 3, h - 3))
        box = ImageChops.difference(im, Image.new("RGB", im.size, bg)).getbbox()
        if box:
            im.crop((0, 0, w, min(h, box[3] + 20))).save(path)
    except ImportError:
        pass
    for cmd in (["pngquant", "--quality=72-96", "--speed", "1", "--force",
                 "--output", str(path), str(path)],
                ["optipng", "-quiet", "-o2", str(path)]):
        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=120)
        except FileNotFoundError:
            pass


for name, html, width in SHOTS:
    render(name, html, width)
    finish(OUT / f"{name}.png")
    print(f"  {name}.png  {(OUT / f'{name}.png').stat().st_size/1024:.0f} KB")

# ---- the front page ----------------------------------------------------------
hero = re.sub(r'(<summary>\s*)(<span class="hl">.*?</span></span>)\s*(<a class="applybtn".*?</a>)',
              lambda m: m.group(1) + m.group(3) + "\n" + m.group(2), page, flags=re.S)
hero = hero.replace("</style>", "</style>\n<style>" + fix + "</style>", 1)
hp = OUT / "_hero.html"
hp.write_text(hero)
subprocess.run(["wkhtmltoimage", "--quiet", "--format", "png", "--width", "1550",
                "--crop-x", "0", "--crop-y", "0", "--crop-w", "1550", "--crop-h", "985",
                "--enable-local-file-access", str(hp), str(OUT / "newspaper.png")],
               check=True, capture_output=True, timeout=300)
hp.unlink()
finish(OUT / "newspaper.png")
print(f"  newspaper.png  {(OUT / 'newspaper.png').stat().st_size/1024:.0f} KB")
