"""Builds out/report.html: the page to show in the presentation."""

import datetime
import html
from collections import defaultdict


def _e(x):
    return html.escape(str(x))


def _state_label(model, st):
    hint = model.hints.get(st)
    return f"{st} · {hint}" if hint else st


def _mermaid(model):
    lines = ["stateDiagram-v2", "  direction LR"]
    for st in model.states:
        lines.append(f'  state "{_state_label(model, st)}" as {st}')
    lines.append(f"  [*] --> {model.initial}")
    edges = defaultdict(list)
    for st, row in model.transitions.items():
        for cmd, (out, nxt) in row.items():
            edges[(st, nxt)].append(f"{cmd}/{out}")
    for (a, b), labels in edges.items():
        lines.append(f"  {a} --> {b} : {', '.join(labels)}")
    return "\n".join(lines)


def _seq(cmds):
    return " ".join(cmds)


def _bar(pct, cls):
    return (f'<div class="bar"><div class="fill {cls}" style="width:{pct}%"></div>'
            f'<span>{pct}%</span></div>')


def write_report(path, model, stats, twin_res, base_res, cov, swap, n_record):
    trans_rows = []
    for st, row in model.transitions.items():
        for cmd, (out, nxt) in row.items():
            moved = "" if nxt == st else ' class="moved"'
            trans_rows.append(
                f"<tr><td>{_e(_state_label(model, st))}</td><td><code>{_e(cmd)}</code></td>"
                f"<td><code>{_e(out)}</code></td><td{moved}>{_e(_state_label(model, nxt))}</td></tr>")

    fail_rows = []
    for f in base_res["failures"]:
        fail_rows.append(
            f"<tr><td><code>{_e(_seq(f['input']))}</code></td>"
            f"<td><code>{_e(_seq(f['expected']))}</code></td>"
            f"<td><code>{_e(_seq(f['got']))}</code></td></tr>")
    if not fail_rows:
        fail_rows.append('<tr><td colspan="3">אין כשלים</td></tr>')

    swap_rows = []
    for (cmd, dev_out), (_, twin_out) in zip(swap["device"], swap["twin"]):
        mark = "✓" if dev_out == twin_out else "✗"
        swap_rows.append(
            f"<tr><td><code>{_e(cmd)}</code></td><td><code>{_e(dev_out)}</code></td>"
            f"<td><code>{_e(twin_out)}</code></td><td>{mark}</td></tr>")

    cex = stats["counterexamples"]
    cex_text = ("לא נדרשו: ההשערה הראשונה עברה את כל הבדיקות האקראיות."
                if not cex else "; ".join(_seq(c) for c in cex))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    page = f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BlackBox Twin POC</title>
<style>
:root {{
  --bg:#f6f5f1; --card:#fffdf8; --ink:#1d2330; --muted:#5b6472; --line:#e2dfd6;
  --twin:#2563eb; --base:#d9822b; --good:#1f7a4d; --bad:#b4372f;
}}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14171d; --card:#1c2029; --ink:#e8e6e1; --muted:#a3abb8; --line:#2e3440;
          --twin:#6b9bff; --base:#f0a352; --good:#5cc48d; --bad:#f07a70; }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
       font:16px/1.55 "Segoe UI", Arial, sans-serif; }}
main {{ max-width:1040px; margin:0 auto; padding:32px 16px 64px; }}
h1 {{ font-size:34px; margin:0 0 4px; }}
h2 {{ font-size:22px; margin:40px 0 12px; }}
.sub {{ color:var(--muted); margin:0 0 24px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }}
.card b {{ display:block; font-size:30px; line-height:1.2; }}
.card span {{ color:var(--muted); font-size:14px; }}
.card.twin b {{ color:var(--twin); }} .card.base b {{ color:var(--base); }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:15px; }}
th, td {{ text-align:right; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; }}
td.moved {{ font-weight:700; }}
code {{ font-family:Consolas, "Courier New", monospace; direction:ltr; unicode-bidi:embed; }}
.ltr {{ direction:ltr; }}
.bar {{ position:relative; background:var(--line); border-radius:6px; height:28px; margin:6px 0 14px; }}
.fill {{ height:100%; border-radius:6px; }}
.fill.twin {{ background:var(--twin); }} .fill.base {{ background:var(--base); }}
.bar span {{ position:absolute; inset-inline-start:10px; top:3px; font-weight:700; color:#fff;
            text-shadow:0 1px 2px rgba(0,0,0,.5); }}
ol li, ul li {{ margin:4px 0; }}
.note {{ color:var(--muted); font-size:14px; }}
pre.mermaid {{ background:transparent; margin:0; text-align:center; }}
</style>
</head>
<body>
<main>
<h1>BlackBox Twin — הוכחת היתכנות</h1>
<p class="sub">המערכת למדה את ההתנהגות של מכשיר בלי לראות את הקוד שלו, ובנתה תאום שמתנהג כמוהו. נוצר ב-{now}.</p>

<div class="cards">
  <div class="card"><b>{stats['states']}</b><span>מצבים שהתגלו</span></div>
  <div class="card"><b>{stats['device_runs']}</b><span>ניסויים מול המכשיר</span></div>
  <div class="card"><b>{stats['seconds']} ש׳</b><span>זמן למידה</span></div>
  <div class="card twin"><b>{twin_res['seq_pct']}%</b><span>התאום צדק ברצפים חדשים</span></div>
  <div class="card base"><b>{base_res['seq_pct']}%</b><span>Record &amp; Replay צדק</span></div>
</div>

<h2>מכונת המצבים שנלמדה</h2>
<div class="panel ltr">
<pre class="mermaid">
{_mermaid(model)}
</pre>
</div>
<p class="note">כל חץ: <code>פקודה/תשובה</code>. שם המצב נבחר אוטומטית (s0, s1…), ולידו התשובה ל-STATUS רק כדי שיהיה קל לקרוא. שים לב ששני מצבים עונים <code>LED_ON</code> ל-STATUS, ובכל זאת המערכת זיהתה שהם שונים.</p>

<div class="panel">
<table>
<tr><th>מצב</th><th>פקודה</th><th>תשובה</th><th>מצב הבא</th></tr>
{''.join(trans_rows)}
</table>
</div>

<h2>האם התאום באמת מתנהג כמו המכשיר?</h2>
<div class="panel">
<p>נבדקו <b>{twin_res['seq_total']}</b> רצפי פקודות <b>חדשים</b> שהמערכת לא שלחה בזמן הלמידה (באורך 3–15). כל רצף נשלח גם למכשיר וגם למועמד, והתשובות הושוו.</p>
<p><b>התאום שנלמד</b> — רצפים זהים לגמרי ({twin_res['seq_ok']}/{twin_res['seq_total']}):</p>
{_bar(twin_res['seq_pct'], 'twin')}
<p><b>Record &amp; Replay</b> (בלי מצבים, "התשובה הנפוצה לכל פקודה", קיבל {n_record} הקלטות) — ({base_res['seq_ok']}/{base_res['seq_total']}):</p>
{_bar(base_res['seq_pct'], 'base')}
<table>
<tr><th></th><th>רצפים נכונים</th><th>תשובות בודדות נכונות</th></tr>
<tr><td>התאום</td><td>{twin_res['seq_pct']}%</td><td>{twin_res['step_pct']}% ({twin_res['step_ok']}/{twin_res['step_total']})</td></tr>
<tr><td>Record &amp; Replay</td><td>{base_res['seq_pct']}%</td><td>{base_res['step_pct']}% ({base_res['step_ok']}/{base_res['step_total']})</td></tr>
</table>
<p class="note">כיסוי: הבדיקות עברו ב-{cov['covered']} מתוך {cov['total']} המעברים שנלמדו ({cov['pct']}%).</p>
</div>

<h2>איפה Record &amp; Replay נכשל</h2>
<div class="panel">
<table>
<tr><th>רצף</th><th>המכשיר ענה</th><th>Record &amp; Replay ענה</th></tr>
{''.join(fail_rows)}
</table>
<p class="note">הוא תמיד עונה אותו דבר לאותה פקודה, ולכן לא יכול לדעת שה-ON השני מחזיר אזהרה וה-ON השלישי מכניס לתקלה.</p>
</div>

<h2>החלפת המכשיר בתאום</h2>
<div class="panel">
<p>אפליקציית המפעל הריצה את אותו תרחיש פעמיים. ההבדל היחיד: הפורט שאליו היא מתחברת.</p>
<table>
<tr><th>פקודה</th><th>מכשיר (פורט {swap['device_port']})</th><th>תאום (פורט {swap['twin_port']})</th><th></th></tr>
{''.join(swap_rows)}
</table>
</div>

<h2>איך זה עבד</h2>
<div class="panel">
<ol>
<li>המערכת קיבלה רק כתובת, רשימת פקודות מותרות (<code>{_e(', '.join(model.alphabet))}</code>) ופקודת איפוס (<code>RESET</code>).</li>
<li>מנוע הלמידה (L*) שלח ניסויים: איפוס, רצף פקודות, רישום התשובות. {stats['device_runs_table']} ניסויים לבניית הטבלה.</li>
<li>שורות עם תשובות שונות = מצבים שונים. כך נבנתה השערה של {stats['states']} מצבים.</li>
<li>ההשערה נבדקה מול המכשיר ב-{stats['device_runs_check']} רצפים אקראיים. דוגמאות נגדיות: {_e(cex_text)}</li>
<li>המודל נשמר ל-<code>model.json</code>, והתאום נטען ממנו. לא נכתב קוד חדש למכשיר הזה.</li>
</ol>
</div>

<h2>גבולות</h2>
<div class="panel">
<ul>
<li>זה מכשיר מדומה, עם פרוטוקול טקסט פשוט מעל TCP. השלב הבא: ESP32 אמיתי ו-AWS IoT Core.</li>
<li>הבדיקה האקראית לא מוכיחה שהמודל מושלם. היא מראה שלא נמצא הבדל ב-{twin_res['seq_total']} רצפים חדשים.</li>
<li>מצב פנימי שלא משפיע אף פעם על התשובות לא ניתן לגלות מבחוץ.</li>
<li>תשובות לפקודות מחוץ לרשימה המותרת לא נלמדו.</li>
</ul>
</div>
</main>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs";
  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  mermaid.initialize({{ startOnLoad: true, theme: dark ? "dark" : "default" }});
</script>
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
