"""Build the "Otwarte AED" logo: master SVGs and PNG / JPG / PDF exports.

The sign is constructed, not drawn: everything is a multiple of the module M (the stroke width).
The wordmark is Space Grotesk Bold (SIL OFL 1.1), converted to outlines, so the SVGs need no font.

Run from anywhere:  python build_logo.py   (needs fonttools, uharfbuzz, cairosvg, pillow; see requirements.txt)
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
LOGO = BRAND / "logo"
WEB = BRAND / "web"

# ---------------------------------------------------------------- palette
RED = "#E6013A"  # Czerwień Puls
INK = "#0B1F28"  # Granat Noc
WHITE = "#FFFFFF"
BLACK = "#000000"

# ---------------------------------------------------------------- the sign
M = 12.0  # module = stroke width, in SVG user units
R = 2 * M  # centreline radius of each lobe
CY = 2.5 * M  # lobe centres sit 2.5 M below the top edge
MID = 4.5 * M  # vertical axis of symmetry (sign is 9 M wide)
ARC_TRIM = 15.0  # degrees cut off each lobe next to the opening
LINE_TRIM = 0.25 * M  # length cut off each arm of the "<" next to the opening


def _p(x: float, y: float) -> str:
    return f"{x:.2f},{y:.2f}".replace(".00", "")


def _arc_band(cx: float, cy: float, t0: float, t1: float) -> str:
    """Annular sector of the lobe, from angle t0 to t1 (degrees, clockwise on screen)."""
    ro, ri = R + M / 2, R - M / 2
    a0, a1 = math.radians(t0), math.radians(t1)
    large = 1 if abs(t1 - t0) > 180 else 0
    o0 = (cx + ro * math.cos(a0), cy + ro * math.sin(a0))
    o1 = (cx + ro * math.cos(a1), cy + ro * math.sin(a1))
    i0 = (cx + ri * math.cos(a0), cy + ri * math.sin(a0))
    i1 = (cx + ri * math.cos(a1), cy + ri * math.sin(a1))
    return (
        f"M{_p(*o0)}A{ro:g},{ro:g} 0 {large} 1 {_p(*o1)}"
        f"L{_p(*i1)}A{ri:g},{ri:g} 0 {large} 0 {_p(*i0)}Z"
    )


def sign_geometry(arc_trim: float = ARC_TRIM, line_trim: float = LINE_TRIM) -> dict:
    """The sign is a heart written the way the internet writes one, "<3", turned 90 degrees.

    - the "3" = two lobes, each a 225-degree arc of radius 2 M (centreline);
    - the "<" = a chevron whose arms are tangent to the lobes at 45 degrees;
    - two openings where the "3" and the "<" do not touch: the heart is open;
    - a spark (lightning bolt) inside: the discharge that restores the rhythm.
    """
    c1x, c2x = MID - R, MID + R
    t = math.radians(135)
    tangent = (c1x + R * math.cos(t), CY + R * math.sin(t))  # where the left arm meets the left lobe
    tip_y = tangent[1] + (MID - tangent[0])  # 45-degree arm reaches the axis here
    k = 1 / math.sqrt(2)
    s = (tangent[0] + line_trim * k, tangent[1] + line_trim * k)  # start of the left arm (centreline)
    n = M / 2 * k
    so, si = (s[0] - n, s[1] + n), (s[0] + n, s[1] - n)  # outer / inner edge of the arm
    to, ti = (MID, tip_y + M / 2 * math.sqrt(2)), (MID, tip_y - M / 2 * math.sqrt(2))
    mirror = lambda p: (2 * MID - p[0], p[1])  # noqa: E731
    chevron = (
        f"M{_p(*si)}L{_p(*ti)}L{_p(*mirror(si))}L{_p(*mirror(so))}"
        f"L{_p(*to)}L{_p(*so)}Z"
    )
    lobes = _arc_band(c1x, CY, 135 + arc_trim, 360) + _arc_band(c2x, CY, 180, 405 - arc_trim)

    # spark: 2.25 M wide, 2.75 M tall, centred on the axis between the lobes' meeting point and the chevron
    bw, bh, bcy = 2.25 * M, 2.75 * M, 4.4 * M
    pts = [(0.64, 0), (0.06, 0.60), (0.44, 0.60), (0.34, 1.0), (0.94, 0.38), (0.56, 0.38)]
    spark = "M" + "L".join(_p(MID - bw / 2 + x * bw, bcy - bh / 2 + y * bh) for x, y in pts) + "Z"

    height = to[1]
    return {
        "lobes": lobes,
        "chevron": chevron,
        "spark": spark,
        "width": 9 * M,
        "height": height,
        "tip_y": tip_y,
        "tangent": tangent,
    }


# ---------------------------------------------------------------- the wordmark
FONT_FILE = HERE / "fonts" / "SpaceGrotesk.ttf"
_static_cache: dict[int, TTFont] = {}


def _static_font(weight: int) -> tuple[TTFont, bytes]:
    if weight not in _static_cache:
        vf = TTFont(FONT_FILE)
        _static_cache[weight] = instancer.instantiateVariableFont(vf, {"wght": weight})
    font = _static_cache[weight]
    buf = io.BytesIO()
    font.save(buf)
    return font, buf.getvalue()


def text_path(text: str, size: float, x: float, baseline: float, weight: int = 700, tracking: float = 0.0):
    """Shape text with HarfBuzz (kerning) and return (svg path d, advance width)."""
    font, data = _static_font(weight)
    upem = font["head"].unitsPerEm
    hbfont = hb.Font(hb.Face(data))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    glyphset = font.getGlyphSet()
    order = font.getGlyphOrder()
    scale = size / upem
    pen = SVGPathPen(glyphset)
    cursor = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        gx = x + (cursor + pos.x_offset) * scale
        tpen = TransformPen(pen, (scale, 0, 0, -scale, gx, baseline - pos.y_offset * scale))
        glyphset[name].draw(tpen)
        cursor += pos.x_advance + tracking * upem
    return pen.getCommands(), (cursor - tracking * upem) * scale


def cap_height_ratio(weight: int = 700) -> float:
    font, _ = _static_font(weight)
    return font["OS/2"].sCapHeight / font["head"].unitsPerEm


# ---------------------------------------------------------------- lockups
PAD = 0.5 * M  # small margin inside every file; the full clear space (2 M) is defined in the brand book


def svg_doc(width: float, height: float, body: str, title: str, bg: str | None = None) -> str:
    rect = f'<rect x="{-PAD:g}" y="{-PAD:g}" width="{width + 2 * PAD:g}" height="{height + 2 * PAD:g}" fill="{bg}"/>' if bg else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-PAD:g} {-PAD:g} {width + 2 * PAD:g} {height + 2 * PAD:g}" '
        f'width="{width + 2 * PAD:g}" height="{height + 2 * PAD:g}" role="img" aria-label="{title}">'
        f"<title>{title}</title>{rect}{body}</svg>\n"
    )


def sign_body(g: dict, lobes: str, chevron: str, spark: str | None, dx: float = 0, dy: float = 0) -> str:
    tr = f' transform="translate({dx:g} {dy:g})"' if dx or dy else ""
    out = f'<g{tr}><path fill="{lobes}" d="{g["lobes"]}"/><path fill="{chevron}" d="{g["chevron"]}"/>'
    if spark:
        out += f'<path fill="{spark}" d="{g["spark"]}"/>'
    return out + "</g>"


def wordmark(x: float, sign_h: float, c1: str, c2: str) -> tuple[str, float]:
    """"Otwarte AED" in one line; cap height 3.5 M, caps centred on the lobes' widest point and the arms."""
    cap = 3.5 * M
    size = cap / cap_height_ratio()
    baseline = 6.15 * M  # baseline sits level with the inner tip of the chevron's opening zone (see book)
    d1, w1 = text_path("Otwarte", size, x, baseline, tracking=-0.01)
    space = 0.27 * size
    d2, w2 = text_path("AED", size, x + w1 + space, baseline, tracking=0.0)
    body = f'<path fill="{c1}" d="{d1}"/><path fill="{c2}" d="{d2}"/>'
    return body, w1 + space + w2


SCHEMES = {
    # name: (lobes, chevron, spark, word1, word2, background for JPG)
    "kolor": (RED, INK, RED, INK, RED, WHITE),
    "kolor-ciemne-tlo": (RED, WHITE, RED, WHITE, RED, INK),
    "czerwony": (RED, RED, RED, RED, RED, WHITE),
    "mono": (BLACK, BLACK, BLACK, BLACK, BLACK, WHITE),
    "negatyw": (WHITE, WHITE, WHITE, WHITE, WHITE, INK),
}


def build_svgs() -> dict[str, tuple[str, str]]:
    """Return {file stem: (svg text, jpg background)}."""
    g = sign_geometry()
    out = {}
    gap = 1.75 * M
    for scheme, (cl, cc, cs, w1, w2, bg) in SCHEMES.items():
        # sign only
        out[f"otwarte-aed-znak-{scheme}"] = (
            svg_doc(g["width"], g["height"], sign_body(g, cl, cc, cs), "Otwarte AED"),
            bg,
        )
        # horizontal lockup
        words, ww = wordmark(g["width"] + gap, g["height"], w1, w2)
        width = g["width"] + gap + ww
        out[f"otwarte-aed-poziomy-{scheme}"] = (
            svg_doc(width, g["height"], sign_body(g, cl, cc, cs) + words, "Otwarte AED"),
            bg,
        )
    # simplified sign for 16-32 px (favicon): no spark
    out["otwarte-aed-znak-favicon"] = (svg_doc(g["width"], g["height"], sign_body(g, RED, RED, None), "Otwarte AED"), WHITE)
    return out


def export(stem: str, svg: str, bg: str) -> None:
    (LOGO / f"{stem}.svg").write_text(svg)
    data = svg.encode()
    cairosvg.svg2pdf(bytestring=data, write_to=str(LOGO / f"{stem}.pdf"))
    for width, suffix in ((2048, ""), (512, "-512")):
        png = cairosvg.svg2png(bytestring=data, output_width=width)
        (LOGO / f"{stem}{suffix}.png").write_bytes(png)
        if suffix == "":
            img = Image.open(io.BytesIO(png)).convert("RGBA")
            flat = Image.new("RGB", img.size, bg)
            flat.paste(img, mask=img.split()[3])
            flat.save(LOGO / f"{stem}.jpg", quality=95, subsampling=0)


def export_favicon(svg: str) -> None:
    data = svg.encode()
    for px in (16, 32, 48, 180, 192):
        png = cairosvg.svg2png(bytestring=data, output_width=px)
        # square canvas, sign centred
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        sq = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        sq.paste(img, (0, (px - img.height) // 2), img)
        sq.save(LOGO / f"favicon-{px}.png")
    imgs = [Image.open(LOGO / f"favicon-{px}.png") for px in (16, 32, 48)]
    imgs[2].save(LOGO / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=imgs[:2])


def main() -> None:
    LOGO.mkdir(exist_ok=True)
    WEB.mkdir(exist_ok=True)
    svgs = build_svgs()
    for stem, (svg, bg) in svgs.items():
        export(stem, svg, bg)
    export_favicon(svgs["otwarte-aed-znak-favicon"][0])
    for stem in (
        "otwarte-aed-znak-kolor",
        "otwarte-aed-poziomy-kolor",
        "otwarte-aed-poziomy-kolor-ciemne-tlo",
        "otwarte-aed-poziomy-negatyw",
        "otwarte-aed-znak-favicon",
    ):
        (WEB / f"{stem}.svg").write_text(svgs[stem][0])
    print(f"wrote {len(svgs)} variants to {LOGO}")


if __name__ == "__main__":
    main()
