"""Render deliverables/wzorcowy-zakres-danych-aed.xlsx as a spreadsheet-like HTML page (out/scope.html) for the demo,
so the video can show the real file's sheets without an office suite. Every cell comes from the workbook.

    python -I gen-scope.py        (needs openpyxl)
"""

import html
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
XLSX = HERE.parent.parent / "deliverables" / "wzorcowy-zakres-danych-aed.xlsx"
OUT = HERE / "out" / "scope.html"
WIDTHS = {  # px per column, by sheet
    "Wzorcowy zakres danych": [170, 170, 170, 120, 150, 140, 130, 140, 160, 150, 150],
    "Słownik pól": [220, 250, 520, 90, 260, 150, 100, 260, 160],
    "Dozwolone wartości": [240, 300, 280, 520],
    "Instrukcja": [70, 1500],
}


def col_letter(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def sheet_html(ws, idx):
    rows = [r for r in ws.iter_rows(values_only=True)]
    ncols = max((len(r) for r in rows), default=1)
    widths = WIDTHS.get(ws.title, []) + [140] * ncols
    head = "".join(f'<th style="width:{widths[i]}px">{col_letter(i)}</th>' for i in range(ncols))
    body = []
    for n, r in enumerate(rows, start=1):
        cls = "hdr" if n == 1 and ws.title != "Instrukcja" else ""
        if ws.title == "Wzorcowy zakres danych" and n > 1:
            cls = "ex"
        if ws.title == "Instrukcja" and r and r[0] and n == 1:
            cls = "title"
        cells = "".join(f"<td>{html.escape(str(c)) if c is not None else ''}</td>" for c in list(r) + [None] * (ncols - len(r)))
        body.append(f'<tr class="{cls}"><th>{n}</th>{cells}</tr>')
    for n in range(len(rows) + 1, len(rows) + 25):
        body.append(f"<tr><th>{n}</th>" + "<td></td>" * ncols + "</tr>")
    return (f'<div class="sheet{" on" if idx == 0 else ""}" data-name="{html.escape(ws.title)}"><table>'
            f'<thead><tr><th class="corner"></th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>')


def main():
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    sheets = "".join(sheet_html(ws, i) for i, ws in enumerate(wb.worksheets))
    tabs = "".join(f'<button class="tab{" on" if i == 0 else ""}" data-name="{html.escape(ws.title)}">{html.escape(ws.title)}</button>'
                   for i, ws in enumerate(wb.worksheets))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(f"""<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>{XLSX.name}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
 html,body{{margin:0;height:100%;font-family:Inter,sans-serif;background:#fff;overflow:hidden}}
 .bar{{height:54px;background:#1d6f42;color:#fff;display:flex;align-items:center;padding:0 22px;font-size:19px;gap:14px}}
 .bar b{{font-weight:600}} .bar span{{opacity:.8;font-size:16px}}
 .fx{{height:38px;border-bottom:1px solid #d4d4d4;display:flex;align-items:center;font-size:15px;color:#333}}
 .fx .ref{{width:90px;border-right:1px solid #d4d4d4;height:100%;display:flex;align-items:center;justify-content:center}}
 .fx .val{{padding-left:14px;white-space:nowrap;overflow:hidden}}
 .grid{{position:absolute;top:93px;bottom:46px;left:0;right:0;overflow:auto}}
 .sheet{{display:none}} .sheet.on{{display:block}}
 table{{border-collapse:collapse;table-layout:fixed;font-size:15px}}
 th{{background:#f3f3f3;color:#555;font-weight:400;border:1px solid #d4d4d4;height:26px;position:sticky;top:0}}
 tbody th{{position:sticky;left:0;width:46px;min-width:46px;z-index:1}}
 th.corner{{left:0;z-index:2;width:46px}}
 td{{border:1px solid #e2e2e2;padding:5px 8px;vertical-align:top;white-space:pre-line;overflow:hidden;max-height:90px;color:#222}}
 tr.hdr td{{background:#0b1f28;color:#fff;font-weight:600}}
 tr.ex td{{background:#fff6c4}}
 tr.title td{{font-size:22px;font-weight:600}}
 tr.sel td{{background:#e8f0fe}}
 .tabs{{position:absolute;bottom:0;left:0;right:0;height:46px;background:#f3f3f3;border-top:1px solid #d4d4d4;display:flex;padding-left:60px}}
 .tab{{border:0;background:none;font:inherit;font-size:16px;padding:0 22px;color:#444;cursor:pointer}}
 .tab.on{{background:#fff;color:#1d6f42;font-weight:600;border-bottom:3px solid #1d6f42}}
</style></head><body>
<div class="bar"><b>{XLSX.name}</b><span>Misja AED · wzorcowy zakres danych o defibrylatorach</span></div>
<div class="fx"><div class="ref" id="ref">A1</div><div class="val" id="val"></div></div>
<div class="grid" id="grid">{sheets}</div>
<div class="tabs">{tabs}</div>
<script>
 const grid=document.getElementById('grid');
 document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{{
   document.querySelectorAll('.tab,.sheet').forEach(e=>e.classList.toggle('on',e.dataset.name===t.dataset.name));
   grid.scrollTo(0,0);
 }});
 grid.addEventListener('click',e=>{{const td=e.target.closest('td'); if(!td) return;
   document.getElementById('val').textContent=td.textContent;}});
</script></body></html>""")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
