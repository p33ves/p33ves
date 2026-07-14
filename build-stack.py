"""Build stack.svg: the tech-stack badges, rendered here, served from this repo.

No shields.io, no skillicons, no runtime dependency on anyone's server. Logos are
fetched once from Simple Icons and Devicon (both open source) and inlined.

    python3 build-stack.py

Simple Icons dropped Azure/AWS/dbt/Power BI over trademark complaints, so Azure
and AWS come from Devicon instead, and the three with no icon anywhere render as
text-only pills.
"""

import re
import urllib.request
import xml.etree.ElementTree as ET
import xml.sax.saxutils as sax
from pathlib import Path

SI = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{}.svg"
DEV = "https://raw.githubusercontent.com/devicons/devicon/master/icons/{}.svg"

BG, STROKE, INK, LABEL = "#1F2430", "#30363D", "#E6EDF3", "#8B949E"
H, PAD, ICON, GAP, ROW_GAP, COL = 26, 11, 16, 7, 9, 84
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"

# (text, simple-icons slug or None, colour). Kafka and OpenJDK are black in the
# source, which is invisible on a dark pill, so they get forced to white.
ROWS = [
    ("Data", [
        ("Databricks", "databricks", "#FF3621"), ("Spark", "apachespark", "#E25A1C"),
        ("Kafka", "apachekafka", "#FFFFFF"), ("Airflow", "apacheairflow", "#017CEE"),
        ("dbt", None, None), ("Snowflake", "snowflake", "#29B5E8"),
    ]),
    ("Cloud", [
        ("Azure", "@azure/azure-original", None), ("AWS", "@amazonwebservices/amazonwebservices-plain-wordmark", None),
        ("GCP", "googlecloud", "#4285F4"), ("Terraform", "terraform", "#9A6FE0"),
        ("Docker", "docker", "#2496ED"), ("Kubernetes", "kubernetes", "#5C8AE6"),
    ]),
    ("Code", [
        ("Python", "python", "#6FA8DC"), ("SQL", None, None), ("Scala", "scala", "#DC322F"),
        ("Java", "openjdk", "#FFFFFF"), ("Bash", "gnubash", "#4EAA25"),
    ]),
    ("Analytics", [
        ("Power BI", None, None), ("MLflow", "mlflow", "#0194E2"),
        ("scikit-learn", "scikitlearn", "#F7931E"), ("Grafana", "grafana", "#F46800"),
        ("Prometheus", "prometheus", "#E6522C"),
    ]),
]

# Rough Helvetica advance widths at 12px. Only needs to be close: it sets pill width.
NARROW, WIDE = "iljtfr.-", "mwMW"


def text_width(s, size=12):
    w = sum(3.7 if c in NARROW else 10.0 if c in WIDE else 8.0 if c.isupper() else 6.7 for c in s)
    return w * size / 12


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode()


def logo(slug, colour, x, y):
    """Return SVG for one 16x16 logo at (x, y)."""
    if slug.startswith("@"):  # Devicon: full-colour, 128-unit box, keep as nested <svg>
        svg = fetch(DEV.format(slug[1:]))
        inner = svg[svg.index(">", svg.index("<svg")) + 1: svg.rindex("</svg>")]
        return f'<svg x="{x}" y="{y}" width="{ICON}" height="{ICON}" viewBox="0 0 128 128">{inner}</svg>'
    # Simple Icons: one monochrome path in a 24-unit box, so we colour it ourselves
    d = re.search(r'\sd="([^"]+)"', fetch(SI.format(slug))).group(1)
    s = ICON / 24
    return f'<path d="{d}" fill="{colour}" transform="translate({x},{y}) scale({s:.4f})"/>'


def build():
    parts, y, width = [], 14, 0
    for name, items in ROWS:
        parts.append(
            f'<text x="0" y="{y + H / 2 + 4:.0f}" fill="{LABEL}" font-family="{FONT}" '
            f'font-size="11" font-weight="600">{name}</text>'
        )
        x = COL
        for text, slug, colour in items:
            has_icon = slug is not None
            w = PAD + (ICON + GAP if has_icon else 0) + text_width(text) + PAD
            parts.append(
                f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="{H}" rx="6" '
                f'fill="{BG}" stroke="{STROKE}"/>'
            )
            tx = x + PAD
            if has_icon:
                parts.append(logo(slug, colour, round(tx), y + (H - ICON) // 2))
                tx += ICON + GAP
            parts.append(
                f'<text x="{tx:.0f}" y="{y + H / 2 + 4:.0f}" fill="{INK}" font-family="{FONT}" '
                f'font-size="12">{sax.escape(text)}</text>'
            )
            x += w + 8
        width = max(width, x)
        y += H + ROW_GAP
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{y - ROW_GAP + 14:.0f}" '
        f'viewBox="0 0 {width:.0f} {y - ROW_GAP + 14:.0f}" role="img" '
        f'aria-label="Tech stack">{"".join(parts)}</svg>'
    )

    ET.fromstring(svg)  # fails loudly rather than pushing a broken image to the profile
    ids = re.findall(r'id="([^"]+)"', svg)
    assert len(ids) == len(set(ids)), f"duplicate ids collide across logos: {ids}"
    return svg


if __name__ == "__main__":
    out = Path(__file__).parent / "stack.svg"
    out.write_text(build())
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")
