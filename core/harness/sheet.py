"""Contact sheet and summary table for one `shoot` run."""
from html import escape

HEIGHT_FLAG = 0.10  # page taller by more than 10% at 1280 px

CSS = """
:root { --bg:#fafafa; --fg:#1d1d1f; --muted:#6b6b70; --line:#dcdce0; --card:#fff;
        --bad:#b3261e; --badbg:#fde7e5; --good:#1b6e35; --goodbg:#e3f4e8; }
@media (prefers-color-scheme: dark) { :root { --bg:#16161a; --fg:#ececf0; --muted:#9a9aa3;
        --line:#34343c; --card:#1f1f25; --bad:#ff8a80; --badbg:#3b1d1b; --good:#7fd89a; --goodbg:#16301f; } }
* { box-sizing: border-box; }
body { margin:0; padding:16px; background:var(--bg); color:var(--fg);
       font:14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
h1 { font-size:20px; margin:0 0 4px; } h2 { font-size:17px; margin:32px 0 8px; }
.meta { color:var(--muted); margin:0 0 16px; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; background:var(--card); }
th, td { border:1px solid var(--line); padding:4px 8px; text-align:left; vertical-align:top; white-space:nowrap; }
th { font-weight:600; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
.flag { color:var(--bad); background:var(--badbg); font-weight:600; }
.ok { color:var(--good); background:var(--goodbg); }
.pair { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:8px 0 20px;
        padding:8px; border:1px solid var(--line); background:var(--card); }
.pair h3 { grid-column:1 / -1; font-size:13px; margin:0; color:var(--muted); font-weight:600; }
.pair figure { margin:0; min-width:0; }
.pair figcaption { font-size:12px; color:var(--muted); margin-bottom:4px; }
.shot { max-height:1400px; overflow:auto; border:1px solid var(--line); background:#fff; }
.pair img { display:block; max-width:100%; }
.err { color:var(--bad); font-size:12px; white-space:pre-wrap; }
a { color:inherit; }
"""


def pct(before, after):
    if not before or after is None:
        return None
    return (after - before) / float(before)


def page_summary(page, shots, sides):
    """Numbers for one summary row, from the 1280 px shots in the first mode."""
    ref = {}
    for shot in shots:
        if shot['label'] == page['label'] and shot['width'] == 1280 and shot['mode'] == shots[0]['mode']:
            ref[shot['side']] = shot
    before, after = ref.get(sides[0], {}), ref.get(sides[-1], {})
    cells = [s for s in shots if s['label'] == page['label'] and s['side'] == sides[0]]
    identical = sum(1 for s in cells if s.get('identical'))
    delta = pct(before.get('height'), after.get('height'))
    return {
        'status': (before.get('status'), after.get('status')),
        'height': (before.get('height'), after.get('height')),
        'height_delta': delta,
        'height_flag': delta is not None and delta > HEIGHT_FLAG,
        'rows': (before.get('rows'), after.get('rows')),
        'rows_flag': (before.get('rows') is not None and after.get('rows') is not None
                      and after['rows'] < before['rows']),
        'identical': (identical, len(cells)),
    }


def _num(v):
    return '' if v is None else '{:,}'.format(v)


def render(run):
    sides = run['sides']
    pages = run['pages']
    shots = run['shots']
    perf = run.get('perf', {})
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>Harness run %s</title><style>%s</style></head><body>' % (escape(run['id']), CSS)]
    out.append('<h1>Harness run %s</h1>' % escape(run['id']))
    out.append('<p class="meta">%s. Before: %s. After: %s. Frozen at %s. Widths %s, modes %s. %s</p>' % (
        escape(run['mode']), escape(run['side_labels'][sides[0]]), escape(run['side_labels'][sides[-1]]),
        escape(run['frozen_at']), ', '.join(map(str, run['widths'])), ', '.join(run['modes']),
        escape('Wall time %.1f s.' % run['wall_seconds'])))
    for note in run.get('notes', []):
        out.append('<p class="flag">%s</p>' % escape(note))

    out.append('<h2>Summary</h2><div class="scroll"><table><tr><th>Page</th><th>Family</th><th>Status</th>'
               '<th>Height at 1280 (before → after)</th><th>Δ</th><th>Rows above the fold</th>'
               '<th>Identical cells</th>')
    if perf:
        out.append('<th>CSS+JS gzip bytes</th><th>Render ms (median of %d)</th>' % run.get('perf_requests', 20))
    out.append('</tr>')
    for page in pages:
        s = page_summary(page, shots, sides)
        delta = '' if s['height_delta'] is None else '%+.1f%%' % (100 * s['height_delta'])
        rows = '' if s['rows'] == (None, None) else '%s → %s' % (_num(s['rows'][0]), _num(s['rows'][1]))
        same, total = s['identical']
        status = ' / '.join(str(x) for x in s['status'])
        bad_status = any(x != 200 for x in s['status'])
        out.append('<tr><td><a href="#%s">%s</a></td><td>%s</td><td class="%s">%s</td>'
                   '<td class="num">%s → %s</td><td class="num %s">%s</td><td class="num %s">%s</td>'
                   '<td class="num %s">%d / %d</td>' % (
                       escape(page['label']), escape(page['label']), escape(page['family']),
                       'flag' if bad_status else '', escape(status),
                       _num(s['height'][0]), _num(s['height'][1]),
                       'flag' if s['height_flag'] else '', delta,
                       'flag' if s['rows_flag'] else '', rows,
                       'ok' if total and same == total else '', same, total))
        if perf:
            p = perf.get(page['label'], {})
            gz = ' → '.join(_num(p.get(side, {}).get('gzip_bytes')) for side in sides)
            ms = ' → '.join('' if p.get(side, {}).get('render_ms') is None else '%.1f' % p[side]['render_ms']
                            for side in sides)
            out.append('<td class="num">%s</td><td class="num">%s</td>' % (gz, ms))
        out.append('</tr>')
    out.append('</table></div>')

    checks = run.get('checks')
    out.append('<h2>Interaction checks</h2>')
    if checks:
        out.append('<p class="meta">From <code>manage.py test --tag browser</code> at %s.</p>' % escape(checks['ran_at']))
        out.append('<table><tr><th>Check</th><th>Result</th></tr>')
        for name, result in sorted(checks['results'].items()):
            out.append('<tr><td>%s</td><td class="%s">%s</td></tr>' % (
                escape(name), 'ok' if result == 'pass' else 'flag', escape(result)))
        out.append('</table>')
    else:
        out.append('<p class="meta">None recorded. Run <code>python manage.py test --tag browser</code>.</p>')

    if run.get('html'):
        out.append('<h2>Rendered HTML</h2><table><tr><th>Page</th><th>Bytes (before → after)</th><th>Identical</th></tr>')
        for label, h in run['html'].items():
            out.append('<tr><td>%s</td><td class="num">%s → %s</td><td class="%s">%s</td></tr>' % (
                escape(label), _num(h['bytes'][0]), _num(h['bytes'][1]),
                'ok' if h['identical'] else 'flag', 'yes' if h['identical'] else 'no'))
        out.append('</table>')

    for page in pages:
        out.append('<h2 id="%s">%s <small class="meta">%s · %s</small></h2>' % (
            escape(page['label']), escape(page['label']), escape(page['url']), escape(page['covers'])))
        for width in run['widths']:
            for mode in run['modes']:
                cell = {s['side']: s for s in shots
                        if s['label'] == page['label'] and s['width'] == width and s['mode'] == mode}
                if not cell:
                    continue
                same = cell.get(sides[0], {}).get('identical')
                out.append('<div class="pair"><h3>%d px · %s%s</h3>' % (width, mode, ' · identical' if same else ''))
                for side in sides:
                    shot = cell.get(side)
                    out.append('<figure><figcaption>%s</figcaption>' % escape(run['side_labels'][side]))
                    if shot and shot.get('file'):
                        out.append('<div class="shot"><a href="%s"><img loading="lazy" src="%s" alt="%s %s %d px %s"></a></div>' % (
                            escape(shot['file']), escape(shot['file']), escape(page['label']), side, width, mode))
                    if shot and shot.get('error'):
                        out.append('<div class="err">%s</div>' % escape(shot['error']))
                    out.append('</figure>')
                out.append('</div>')
    out.append('</body></html>')
    return '\n'.join(out)
