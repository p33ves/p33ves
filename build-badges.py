"""Build the badge SVGs: rendered here, served from this repo.

    python3 build-badges.py     ->  stack.svg, badges/{portfolio,linkedin,email}.svg

No shields.io, no skillicons. Logos are fetched once from open-source icon sets and
inlined, so nothing is loaded from anyone else's server when the README renders.

Sourcing is a mess for a reason: Simple Icons dropped Azure, AWS, Power BI, dbt and
LinkedIn after trademark complaints, so those come from Devicon, Microsoft's own icon
repo, and the (CC0) SVG Logos collection instead. The portfolio globe is drawn here,
since a generic globe belongs to nobody.
"""

import re
import urllib.request
import xml.etree.ElementTree as ET
import xml.sax.saxutils as sax
from pathlib import Path

SI = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{}.svg"
DEV = "https://raw.githubusercontent.com/devicons/devicon/master/icons/{}.svg"
GB = "https://raw.githubusercontent.com/gilbarbara/logos/main/logos/{}.svg"
MS_POWERBI = "https://raw.githubusercontent.com/microsoft/PowerBI-Icons/main/SVG/Power-BI.svg"

BG, STROKE, INK, LABEL = "#1F2430", "#30363D", "#E6EDF3", "#8B949E"
H, PAD, ICON, GAP, ROW_GAP, COL = 26, 11, 16, 7, 9, 84
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"

# Hand-drawn: nobody owns a sphere or a database cylinder, so there is nothing to
# source, attribute, or have taken down.
DRAWN = {
    "globe": (
        '<g fill="none" stroke="#58A6FF" stroke-width="1.6">'
        '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/>'
        '<path d="M3 12h18M5 6.5h14M5 17.5h14"/></g>'
    ),
    "database": (
        '<g fill="none" stroke="#E6EDF3" stroke-width="1.6">'
        '<ellipse cx="12" cy="5.5" rx="7.5" ry="3"/>'
        '<path d="M4.5 5.5v13c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-13"/>'
        '<path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/></g>'
    ),
}

# (label, icon spec, colour). Spec: "si:<slug>" is a monochrome path we colour ourselves;
# everything else is a full-colour logo we nest as-is and leave alone.
ROWS = [
    ("Data", [
        ("Databricks", "si:databricks", "#FF3621"), ("Spark", "si:apachespark", "#E25A1C"),
        ("Kafka", "si:apachekafka", "#FFFFFF"), ("Airflow", "si:apacheairflow", "#017CEE"),
        ("dbt", "gb:dbt-icon", None), ("Snowflake", "si:snowflake", "#29B5E8"),
    ]),
    ("Cloud", [
        ("Azure", "dev:azure/azure-original", None),
        ("AWS", "dev:amazonwebservices/amazonwebservices-plain-wordmark", None),
        ("GCP", "si:googlecloud", "#4285F4"), ("Terraform", "si:terraform", "#9A6FE0"),
        ("Docker", "si:docker", "#2496ED"), ("Kubernetes", "si:kubernetes", "#5C8AE6"),
    ]),
    ("Code", [
        ("Python", "si:python", "#6FA8DC"), ("SQL", "raw:database", None), ("Scala", "si:scala", "#DC322F"),
        ("Java", "si:openjdk", "#FFFFFF"), ("Bash", "si:gnubash", "#4EAA25"),
    ]),
    ("Analytics", [
        ("Power BI", "ms:powerbi", None), ("MLflow", "si:mlflow", "#0194E2"),
        ("scikit-learn", "si:scikitlearn", "#F7931E"), ("Grafana", "si:grafana", "#F46800"),
        ("Prometheus", "si:prometheus", "#E6522C"),
    ]),
]

LINKS = [("Portfolio", "raw:globe", None), ("LinkedIn", "gb:linkedin-icon", None),
         ("Email", "si:gmail", "#EA4335")]

NARROW, WIDE = "iljtfr.-", "mwMW"


def text_width(s, size=12):
    w = sum(3.7 if c in NARROW else 10.0 if c in WIDE else 8.0 if c.isupper() else 6.7 for c in s)
    return w * size / 12


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode()


def nest(svg, x, y, tag):
    """Inline a full-colour logo, scaled into an ICON-tall box at (x, y).

    IDs are namespaced per logo: Microsoft's Power BI export uses names like
    'paint0_linear' that would otherwise collide with any other gradient.
    """
    svg = re.sub(r"<\?xml.*?\?>|<metadata.*?</metadata>|<!--.*?-->", "", svg, flags=re.DOTALL)
    for ident in set(re.findall(r'id="([^"]+)"', svg)):
        svg = re.sub(rf'id="{re.escape(ident)}"', f'id="{tag}-{ident}"', svg)
        svg = re.sub(rf"url\(#{re.escape(ident)}\)", f"url(#{tag}-{ident})", svg)
    vb = re.search(r'viewBox="([\d.\s-]+)"', svg).group(1).split()
    w, h = float(vb[2]), float(vb[3])
    inner = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
    box = ICON * w / h  # keep the aspect: Power BI's icon is portrait, not square
    return (f'<svg x="{x + (ICON - box) / 2:.1f}" y="{y}" width="{box:.1f}" height="{ICON}" '
            f'viewBox="{" ".join(vb)}">{inner}</svg>')


def icon(spec, colour, x, y, tag):
    kind, _, name = spec.partition(":")
    if kind == "raw":
        return (f'<svg x="{x}" y="{y}" width="{ICON}" height="{ICON}" '
                f'viewBox="0 0 24 24">{DRAWN[name]}</svg>')
    if kind == "si":  # one monochrome path in a 24-unit box: colour it ourselves
        d = re.search(r'\sd="([^"]+)"', fetch(SI.format(name))).group(1)
        return (f'<path d="{d}" fill="{colour}" '
                f'transform="translate({x},{y}) scale({ICON / 24:.4f})"/>')
    url = {"dev": DEV.format(name), "gb": GB.format(name), "ms": MS_POWERBI}[kind]
    return nest(fetch(url), x, y, tag)


def pill(text, spec, colour, x, y, tag):
    w = PAD + (ICON + GAP if spec else 0) + text_width(text) + PAD
    out = [f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="{H}" rx="6" '
           f'fill="{BG}" stroke="{STROKE}"/>']
    tx = x + PAD
    if spec:
        out.append(icon(spec, colour, round(tx), y + (H - ICON) // 2, tag))
        tx += ICON + GAP
    out.append(f'<text x="{tx:.0f}" y="{y + H / 2 + 4:.0f}" fill="{INK}" font-family="{FONT}" '
               f'font-size="12">{sax.escape(text)}</text>')
    return out, w


def wrap(parts, width, height, label):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
           f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" '
           f'aria-label="{label}">{"".join(parts)}</svg>')
    ET.fromstring(svg)  # fail loudly here rather than push a broken image to the profile
    ids = re.findall(r'id="([^"]+)"', svg)
    assert len(ids) == len(set(ids)), "gradient ids collide between logos"
    return svg


def build_stack():
    parts, y, width = [], 14, 0
    for name, items in ROWS:
        parts.append(f'<text x="0" y="{y + H / 2 + 4:.0f}" fill="{LABEL}" font-family="{FONT}" '
                     f'font-size="11" font-weight="600">{name}</text>')
        x = COL
        for i, (text, spec, colour) in enumerate(items):
            got, w = pill(text, spec, colour, x, y, f"{name}{i}".lower())
            parts += got
            x += w + 8
        width = max(width, x)
        y += H + ROW_GAP
    return wrap(parts, width, y - ROW_GAP + 14, "Tech stack")


def build_link(text, spec, colour):
    parts, w = pill(text, spec, colour, 0, 0, text.lower())
    return wrap(parts, w, H, text)


if __name__ == "__main__":
    here = Path(__file__).parent
    (here / "stack.svg").write_text(build_stack())
    (here / "badges").mkdir(exist_ok=True)
    for text, spec, colour in LINKS:
        (here / "badges" / f"{text.lower()}.svg").write_text(build_link(text, spec, colour))
    print("wrote stack.svg and", ", ".join(f"badges/{t.lower()}.svg" for t, _, _ in LINKS))
