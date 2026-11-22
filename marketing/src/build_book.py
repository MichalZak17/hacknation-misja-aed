"""Build the brand book (ksiega-znaku.pdf) from ksiega/ksiega-znaku.html.

The template gets the logo SVGs inline plus drawings generated here (construction, clear space, misuse examples,
applications), then headless Chromium (Playwright) prints it to A4.

    python build_logo.py              # first: logo/*.svg
    python build_book.py [--preview DIR]   # writes ../ksiega-znaku.pdf (and page PNGs into DIR)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import segno
from playwright.sync_api import sync_playwright

from build_logo import (
    INK,
    LOGO,
    BRAND,
    M,
    MID,
    R,
    CY,
    RED,
    WHITE,
    sign_body,
    sign_geometry,
    wordmark,
    text_path,
)

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "ksiega" / "ksiega-znaku.html"
OUT = BRAND / "ksiega-znaku.pdf"

GREEN = "#12B76A"
MIST = "#F2F4F5"
GRAPHITE = "#5B6B73"
GAP = 1.75 * M  # sign to wordmark, same as build_logo


def logo_svg(stem: str, cls: str = "") -> str:
    svg = (LOGO / f"{stem}.svg").read_text().strip()
    svg = re.sub(r' width="[^"]+" height="[^"]+"', "", svg, count=1)
    return svg.replace("<svg ", f'<svg class="{cls}" ', 1) if cls else svg


def lockup(colors=(RED, INK, RED, INK, RED), dx: float = 0, dy: float = 0) -> tuple[str, float, float]:
    """Horizontal lockup as a <g>, with its width and height in SVG units."""
    g = sign_geometry()
    words, ww = wordmark(g["width"] + GAP, g["height"], colors[3], colors[4])
    body = sign_body(g, colors[0], colors[1], colors[2]) + words
    return f'<g transform="translate({dx:g} {dy:g})">{body}</g>', g["width"] + GAP + ww, g["height"]


# ---------------------------------------------------------------- construction
def construction_svg() -> str:
    g = sign_geometry()
    pad = 1.6 * M
    W, H = g["width"] + 2 * pad, 8 * M + 2 * pad + 0.6 * M
    s = [f'<svg viewBox="{-pad:g} {-pad:g} {W:g} {H:g}" class="drawing" xmlns="http://www.w3.org/2000/svg">']
    # module grid
    s.append('<g stroke="#C9D2D6" stroke-width="0.35">')
    for i in range(10):
        s.append(f'<line x1="{i * M:g}" y1="0" x2="{i * M:g}" y2="{8 * M:g}"/>')
    for j in range(9):
        s.append(f'<line x1="0" y1="{j * M:g}" x2="{9 * M:g}" y2="{j * M:g}"/>')
    s.append("</g>")
    # the sign, lightly
    s.append(f'<g opacity="0.16">{sign_body(g, RED, INK, RED)}</g>')
    # construction lines
    c1x, c2x = MID - R, MID + R
    s.append(f'<g fill="none" stroke="{RED}" stroke-width="0.6">')
    for cx in (c1x, c2x):
        s.append(f'<circle cx="{cx:g}" cy="{CY:g}" r="{R:g}" stroke-dasharray="2 1.5"/>')
        s.append(f'<circle cx="{cx:g}" cy="{CY:g}" r="{R + M / 2:g}"/>')
        s.append(f'<circle cx="{cx:g}" cy="{CY:g}" r="{R - M / 2:g}"/>')
        s.append(f'<circle cx="{cx:g}" cy="{CY:g}" r="0.9" fill="{RED}"/>')
    # 45 degree tangents from tangent points to the tip
    tx, ty = g["tangent"]
    tip = g["tip_y"]
    for x0 in (tx, 2 * MID - tx):
        s.append(f'<line x1="{x0:g}" y1="{ty:g}" x2="{MID:g}" y2="{tip:g}" stroke-dasharray="2 1.5"/>')
        # extend the radius to the tangent point to show the 45 degree
    s.append(f'<line x1="{c1x:g}" y1="{CY:g}" x2="{tx:g}" y2="{ty:g}" stroke-width="0.4"/>')
    s.append(f'<line x1="{c2x:g}" y1="{CY:g}" x2="{2 * MID - tx:g}" y2="{ty:g}" stroke-width="0.4"/>')
    s.append(f'<line x1="{MID:g}" y1="{-0.6 * M:g}" x2="{MID:g}" y2="{8.5 * M:g}" stroke-width="0.4" stroke-dasharray="4 2 1 2"/>')
    s.append("</g>")
    # labels
    lab = 'font-family="JetBrains Mono" font-size="3.6" fill="#0B1F28"'
    s.append(f'<text {lab} x="{c1x - 1:g}" y="{CY - 1.6:g}" text-anchor="end">r = 2M</text>')
    s.append(f'<text {lab} x="{tx - 2:g}" y="{ty + 9:g}" text-anchor="end">45°</text>')
    # module marker
    s.append(f'<rect x="{9 * M + 3:g}" y="0" width="{M:g}" height="{M:g}" fill="{INK}"/>')
    s.append(f'<text {lab} x="{9 * M + 3 + M / 2:g}" y="{M + 5:g}" text-anchor="middle">M</text>')
    # dimensions
    dim = f'stroke="{INK}" stroke-width="0.45"'
    y = 8 * M + 0.9 * M
    s.append(f'<line x1="0" y1="{y:g}" x2="{9 * M:g}" y2="{y:g}" {dim}/>')
    s.append(f'<line x1="0" y1="{y - 2:g}" x2="0" y2="{y + 2:g}" {dim}/><line x1="{9 * M:g}" y1="{y - 2:g}" x2="{9 * M:g}" y2="{y + 2:g}" {dim}/>')
    s.append(f'<text {lab} x="{MID:g}" y="{y + 5.5:g}" text-anchor="middle">9M</text>')
    x = -0.8 * M
    s.append(f'<line x1="{x:g}" y1="0" x2="{x:g}" y2="{g["height"]:g}" {dim}/>')
    s.append(f'<line x1="{x - 2:g}" y1="0" x2="{x + 2:g}" y2="0" {dim}/><line x1="{x - 2:g}" y1="{g["height"]:g}" x2="{x + 2:g}" y2="{g["height"]:g}" {dim}/>')
    s.append(f'<text {lab} x="{x - 2.5:g}" y="{g["height"] / 2:g}" text-anchor="middle" transform="rotate(-90 {x - 2.5:g} {g["height"] / 2:g})">8M</text>')
    s.append("</svg>")
    return "".join(s)


def clearspace_svg(sign_only: bool = False) -> str:
    if sign_only:
        g = sign_geometry()
        body, w, h = sign_body(g, RED, INK, RED), g["width"], g["height"]
    else:
        body, w, h = lockup()
    cs = 2 * M
    pad = cs + 0.4 * M
    W, H = w + 2 * pad, h + 2 * pad
    s = [f'<svg viewBox="{-pad:g} {-pad:g} {W:g} {H:g}" class="drawing" xmlns="http://www.w3.org/2000/svg">']
    s.append(f'<rect x="{-cs:g}" y="{-cs:g}" width="{w + 2 * cs:g}" height="{h + 2 * cs:g}" fill="{RED}" fill-opacity="0.07" stroke="{RED}" stroke-width="0.6" stroke-dasharray="3 2"/>')
    s.append(f'<rect x="0" y="0" width="{w:g}" height="{h:g}" fill="#fff" stroke="{RED}" stroke-width="0.4"/>')
    s.append(body)
    # 2M squares in the margins
    lab = 'font-family="JetBrains Mono" font-weight="600" font-size="6.5" fill="#E6013A" text-anchor="middle"'
    for x, y in ((-cs, -cs), (w, -cs), (-cs, h), (w, h)):
        s.append(f'<rect x="{x:g}" y="{y:g}" width="{cs:g}" height="{cs:g}" fill="none" stroke="{RED}" stroke-width="0.5"/>')
    s.append(f'<text {lab} x="{-cs / 2:g}" y="{h / 2 + 2.3:g}">2M</text>')
    s.append(f'<text {lab} x="{w + cs / 2:g}" y="{h / 2 + 2.3:g}">2M</text>')
    s.append(f'<text {lab} x="{w / 2:g}" y="{-cs / 2 + 2.3:g}">2M</text>')
    s.append(f'<text {lab} x="{w / 2:g}" y="{h + cs / 2 + 2.3:g}">2M</text>')
    s.append("</svg>")
    return "".join(s)


def lockup_metrics_svg() -> str:
    """Horizontal lockup with the wordmark's measurements."""
    body, w, h = lockup()
    pad = 1.4 * M
    s = [f'<svg viewBox="{-pad:g} {-pad:g} {w + 2 * pad + 2 * M:g} {h + 2 * pad:g}" class="drawing" xmlns="http://www.w3.org/2000/svg">']
    s.append(body)
    st = f'stroke="{RED}" stroke-width="0.5" fill="none"'
    gx = sign_geometry()["width"]
    base, cap = 6.15 * M, 6.15 * M - 3.5 * M
    s.append(f'<line x1="{gx + GAP - 2:g}" y1="{base:g}" x2="{w + 4:g}" y2="{base:g}" {st} stroke-dasharray="2 1.5"/>')
    s.append(f'<line x1="{gx + GAP - 2:g}" y1="{cap:g}" x2="{w + 4:g}" y2="{cap:g}" {st} stroke-dasharray="2 1.5"/>')
    s.append(f'<rect x="{gx:g}" y="{h + 2:g}" width="{GAP:g}" height="3" fill="{RED}"/>')
    lab = 'font-family="JetBrains Mono" font-weight="600" font-size="6.5" fill="#E6013A"'
    s.append(f'<text {lab} x="{gx + GAP / 2:g}" y="{h + 13:g}" text-anchor="middle">1,75M</text>')
    s.append(f'<text {lab} x="{w + 6:g}" y="{(base + cap) / 2 + 2.3:g}">3,5M</text>')
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- misuse
def misuse_svgs() -> list[tuple[str, str]]:
    body, w, h = lockup()
    pad = 0.8 * M
    vb = f"{-pad:g} {-2.2 * M:g} {w + 2 * pad:g} {h + 4.4 * M:g}"
    cx, cy = w / 2, h / 2

    def wrap(inner: str, defs: str = "", bg: str = "") -> str:
        return f'<svg viewBox="{vb}" xmlns="http://www.w3.org/2000/svg"><defs>{defs}</defs>{bg}{inner}</svg>'

    out = []
    out.append(("Nie rozciągaj ani nie ściskaj", wrap(f'<g transform="translate({cx:g} {cy:g}) scale(1.0 1.45) translate({-cx:g} {-cy:g})">{body}</g>'.replace("scale(1.0 1.45)", "scale(0.78 1.5)"))))
    recol, _, _ = lockup(("#2F80ED", "#27AE60", "#F2C94C", "#7B61FF", "#2F80ED"))
    out.append(("Nie zmieniaj kolorów", wrap(recol)))
    out.append(("Nie obracaj", wrap(f'<g transform="rotate(-14 {cx:g} {cy:g})">{body}</g>')))
    fx = (
        '<filter id="sh" x="-20%" y="-40%" width="140%" height="180%"><feDropShadow dx="3" dy="5" stdDeviation="3" flood-opacity="0.55"/></filter>'
        f'<linearGradient id="gr" x1="0" x2="1"><stop offset="0" stop-color="{RED}"/><stop offset="1" stop-color="#FFB800"/></linearGradient>'
    )
    grad, _, _ = lockup(("url(#gr)", "url(#gr)", "url(#gr)", "url(#gr)", "url(#gr)"))
    out.append(("Nie dodawaj efektów", wrap(f'<g filter="url(#sh)">{grad}</g>', fx)))
    stripes = (
        '<pattern id="pt" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(30)">'
        '<rect width="14" height="14" fill="#F2C94C"/><rect width="7" height="14" fill="#56CCF2"/>'
        '<circle cx="10" cy="4" r="3" fill="#EB5757"/></pattern>'
    )
    out.append(("Nie umieszczaj na niespokojnym tle", wrap(body, stripes, f'<rect x="{-pad:g}" y="{-2.2 * M:g}" width="{w + 2 * pad:g}" height="{h + 4.4 * M:g}" fill="url(#pt)"/>')))
    outline = re.sub(r'fill="(#[0-9A-F]{6})"', r'fill="none" stroke="\1" stroke-width="1.6"', body)
    out.append(("Nie stosuj samego obrysu", wrap(outline)))
    # rearranged: wordmark above the sign, sign to the right
    g = sign_geometry()
    words, ww = wordmark(0, g["height"], INK, RED)
    rearr = f'<g transform="translate({ww + GAP:g} 0)">{sign_body(g, RED, INK, RED)}</g>{words}'
    out.append(("Nie zmieniaj układu elementów", wrap(f'<g transform="translate({(w - ww - GAP - g["width"]) / 2:g} 0)">{rearr}</g>')))
    serif = (
        sign_body(g, RED, INK, RED)
        + f'<text x="{g["width"] + GAP:g}" y="{6.15 * M:g}" font-family="DejaVu Serif, Georgia, serif" font-style="italic" font-size="{3.0 * M / 0.72:g}" fill="{INK}">Otwarte <tspan fill="{RED}">AED</tspan></text>'
    )
    out.append(("Nie zmieniaj kroju pisma", wrap(serif)))
    closed = sign_geometry(arc_trim=0, line_trim=0)
    words2, _ = wordmark(g["width"] + GAP, g["height"], INK, RED)
    out.append(("Nie domykaj serca: prześwity są częścią znaku", wrap(sign_body(closed, RED, INK, RED) + words2)))
    return out


# ---------------------------------------------------------------- applications
def qr_svg(url: str, color: str = INK) -> str:
    qr = segno.make(url, error="m")
    svg = qr.svg_inline(scale=1, dark=color, light=None, border=0, omitsize=True)
    return svg.replace("<svg ", '<svg class="qr" ', 1)


def cover_ghost() -> str:
    """The sign, faint and cropped by the bottom-right corner of the cover."""
    g = sign_geometry()
    return (
        '<svg viewBox="0 0 84 74" xmlns="http://www.w3.org/2000/svg"><g opacity="0.16">'
        f'{sign_body(g, RED, WHITE, RED)}</g></svg>'
    )


def big_sign(colors=(RED, INK, RED)) -> str:
    g = sign_geometry()
    return f'<svg viewBox="0 0 {g["width"]:g} {g["height"]:g}" xmlns="http://www.w3.org/2000/svg">{sign_body(g, *colors)}</svg>'


def lt3_svg() -> tuple[str, str]:
    """'<3' typed in Space Grotesk, then the same turned 90 degrees: the heart."""
    d, w = text_path("<3", 100, 0, 72, weight=500)
    cx, cy, half_h = w / 2, 36, 40
    straight = f'<svg viewBox="-4 -4 {w + 8:g} 84" xmlns="http://www.w3.org/2000/svg"><path fill="{INK}" d="{d}"/></svg>'
    turned = (
        f'<svg viewBox="{cx - half_h:g} {cy - w / 2 - 4:g} {2 * half_h:g} {w + 8:g}" xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="rotate(-90 {cx:g} {cy:g})"><path fill="{INK}" d="{d}"/></g></svg>'
    )
    return straight, turned


def anatomy_svg() -> str:
    """The sign with numbered call-outs for its three parts."""
    g = sign_geometry()
    box = 9.0
    s = [f'<svg viewBox="-20 -8 156 112" class="drawing" xmlns="http://www.w3.org/2000/svg">', sign_body(g, RED, INK, RED)]
    callouts = [  # (number, box x, box y, target x, target y)
        ("1", -18, -6, 12, 12),
        ("2", -18, 80, 30, 66),
        ("3", 124, 74, 56, 58),
    ]
    for n, bx, by, tx, ty in callouts:
        ex = bx + box if bx < tx else bx
        s.append(f'<line x1="{ex:g}" y1="{by + box / 2:g}" x2="{tx:g}" y2="{ty:g}" stroke="{INK}" stroke-width="0.6"/>')
        s.append(f'<circle cx="{tx:g}" cy="{ty:g}" r="1.6" fill="#fff" stroke="{INK}" stroke-width="0.6"/>')
        s.append(f'<rect x="{bx:g}" y="{by:g}" width="{box:g}" height="{box:g}" fill="{INK}"/>')
        s.append(
            f'<text x="{bx + box / 2:g}" y="{by + box / 2 + 2.3:g}" text-anchor="middle" font-family="JetBrains Mono" '
            f'font-weight="600" font-size="6.4" fill="#fff">{n}</text>'
        )
    s.append("</svg>")
    return "".join(s)


def build_html() -> str:
    html = TEMPLATE.read_text()
    lt3a, lt3b = lt3_svg()
    subs = {
        "svg:poziomy-kolor": logo_svg("otwarte-aed-poziomy-kolor"),
        "svg:poziomy-kolor-ciemne-tlo": logo_svg("otwarte-aed-poziomy-kolor-ciemne-tlo"),
        "svg:poziomy-negatyw": logo_svg("otwarte-aed-poziomy-negatyw"),
        "svg:poziomy-mono": logo_svg("otwarte-aed-poziomy-mono"),
        "svg:poziomy-czerwony": logo_svg("otwarte-aed-poziomy-czerwony"),
        "svg:znak-kolor": logo_svg("otwarte-aed-znak-kolor"),
        "svg:znak-kolor-ciemne-tlo": logo_svg("otwarte-aed-znak-kolor-ciemne-tlo"),
        "svg:znak-negatyw": logo_svg("otwarte-aed-znak-negatyw"),
        "svg:znak-mono": logo_svg("otwarte-aed-znak-mono"),
        "svg:znak-czerwony": logo_svg("otwarte-aed-znak-czerwony"),
        "svg:znak-favicon": logo_svg("otwarte-aed-znak-favicon"),
        "svg:big-sign": big_sign(),
        "svg:cover-ghost": cover_ghost(),
        "svg:construction": construction_svg(),
        "svg:clearspace": clearspace_svg(),
        "svg:metrics": lockup_metrics_svg(),
        "svg:lt3a": lt3a,
        "svg:lt3b": lt3b,
        "svg:anatomy": anatomy_svg(),
        "svg:clearspace-sign": clearspace_svg(sign_only=True),
        "svg:qr": qr_svg("https://misja-aed.hackstorm.eu"),
        "svg:qr-white": qr_svg("https://misja-aed.hackstorm.eu", WHITE),
        "misuse": "".join(
            f'<figure class="misuse"><div class="frame">{svg}<span class="x" aria-hidden="true"></span></div><figcaption>{cap}</figcaption></figure>'
            for cap, svg in misuse_svgs()
        ),
    }
    for k, v in subs.items():
        html = html.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[^}]+\}\}", html)
    if left:
        sys.exit(f"unfilled placeholders: {left}")
    return html


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", type=Path, help="also write one PNG per page into this directory")
    args = ap.parse_args()
    html = build_html()
    built = HERE / "ksiega" / "_build.html"
    built.write_text(html)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(built.as_uri())
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")
        page.pdf(path=str(OUT), format="A4", print_background=True, prefer_css_page_size=True)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            page.set_viewport_size({"width": 794, "height": 1123})
            n = page.evaluate("document.querySelectorAll('.page').length")
            for i in range(n):
                el = page.locator(".page").nth(i)
                el.screenshot(path=str(args.preview / f"page-{i + 1:02d}.png"), scale="device")
        browser.close()
    built.unlink()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
