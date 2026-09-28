"""Screenshot the reference pages before and after a change.

    python manage.py shoot --family all --record   # once: hit the live API
    python manage.py shoot --family all            # replay, no network

Before and after are two sides of one run:

- default: this checkout with the `bs` cookie at 3 against 5 (`--bs 3,5`);
- `--ref <git ref>`: that ref, checked out into a temporary worktree, against
  this checkout (`--bs 5` then applies to both sides).

Output goes to the git-ignored `.harness/<run-id>/index.html`: a summary
table and the before/after contact sheet. Signed-in pages need the
HARNESS_TOKEN environment variable and are skipped without it.
"""
import asyncio
import gzip
import hashlib
import json
import os
import re
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.harness import browser, manifest, sheet

REPO_ROOT = os.path.dirname(settings.PROJECT_ROOT)
HARNESS_DIR = os.path.join(REPO_ROOT, '.harness')
FIXTURES_DIR = os.path.join(HARNESS_DIR, 'fixtures')
META_PATH = os.path.join(FIXTURES_DIR, 'meta.json')
HAR_PATH = os.path.join(FIXTURES_DIR, 'browser.har')
SERVE_SCRIPT = os.path.join(REPO_ROOT, 'core', 'harness', 'serve.py')
CHECKS_PATH = os.path.join(HARNESS_DIR, 'checks.json')

VIEWPORT_HEIGHT = 900
PERF_REQUESTS = 20
# Django's masked CSRF token: 64 mixed-case alphanumerics, new on every request.
CSRF = re.compile(r'''(?<=["'])(?=[a-z0-9]*[A-Z])[A-Za-z0-9]{64}(?=["'])''')

SETTLE_JS = """async () => {
  await document.fonts.ready;
  const pending = [...document.images].filter(i => !i.complete && i.loading !== 'lazy');
  await Promise.race([
    Promise.all(pending.map(i => new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); }))),
    new Promise(r => setTimeout(r, 5000)),
  ]);
}"""

METRICS_JS = """(rows) => {
  const doc = document.documentElement;
  const out = {
    height: Math.max(doc.scrollHeight, document.body ? document.body.scrollHeight : 0),
    rows: null,
    times: [...document.querySelectorAll('time')].map(t => t.textContent.trim()),
    reply_box: !!document.querySelector('#post-a-reply-handle'),
  };
  if (rows) {
    out.rows = [...document.querySelectorAll(rows)].filter(e => {
      const r = e.getBoundingClientRect();
      return r.height > 0 && r.bottom <= innerHeight;
    }).length;
  }
  return out;
}"""


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class Server(object):
    """A harness server (core/harness/serve.py) for one source tree."""

    def __init__(self, name, tree, settings_module):
        self.name = name
        self.tree = tree
        self.settings_module = settings_module
        self.port = None
        self.proc = None
        self.log_path = None


class Side(object):
    """One half of the comparison: a server plus the bs value it is asked for."""

    def __init__(self, name, server, bs, label):
        self.name = name
        self.server = server
        self.bs = bs
        self.label = label

    @property
    def port(self):
        return self.server.port


class Command(BaseCommand):
    help = 'Screenshot reference pages before and after a change, from recorded API fixtures.'

    def add_arguments(self, parser):
        parser.add_argument('--family', default='all',
                            help='Template family from core/harness/manifest.py, or all.')
        parser.add_argument('--record', action='store_true',
                            help='Fetch from the live API and browser hosts, writing .harness/fixtures/.')
        parser.add_argument('--widths', default='375,768,1280,1440')
        parser.add_argument('--modes', default='light',
                            help='Comma separated: light, dark. Dark sets the color_mode cookie (BS5-06).')
        parser.add_argument('--ref', help='Git ref for the before side. Default: this checkout.')
        parser.add_argument('--bs', default=None,
                            help='bs value for before,after (e.g. 3,5) or one value for both. '
                                 'Default 3,5 without --ref, none with it. "none" sends nothing.')
        parser.add_argument('--bs-via', choices=('cookie', 'query'), default='cookie')
        parser.add_argument('--html-only', action='store_true',
                            help='Write each page\'s rendered HTML per side for byte comparison; no browser.')
        parser.add_argument('--perf', action='store_true',
                            help='Report gzip CSS+JS bytes per page and median server render time.')
        parser.add_argument('--concurrency', type=int, default=4)
        parser.add_argument('--settle', type=int, default=500, help='Milliseconds to wait after load.')
        parser.add_argument('--run-id', help='Name of the output folder under .harness/.')

    def handle(self, *args, **opts):
        started = time.monotonic()
        try:
            pages = manifest.pages_for(opts['family'])
        except ValueError as e:
            raise CommandError(str(e))
        widths = [int(w) for w in opts['widths'].split(',') if w.strip()]
        modes = [m.strip() for m in opts['modes'].split(',') if m.strip()]
        for mode in modes:
            if mode not in ('light', 'dark'):
                raise CommandError('Unknown mode %r' % mode)

        notes = []
        token = os.environ.get('HARNESS_TOKEN') or None
        if not token:
            skipped = [p.label for p in pages if p.signed_in]
            if skipped:
                msg = 'HARNESS_TOKEN is not set: skipping signed-in pages %s.' % ', '.join(skipped)
                self.stderr.write(msg)
                notes.append(msg)
            pages = [p for p in pages if not p.signed_in]

        mode = 'record' if opts['record'] else 'replay'
        meta = self.session_meta(opts['record'])
        run_id = opts['run_id'] or time.strftime('%Y%m%d-%H%M%S') + ('-record' if opts['record'] else '')
        run_dir = os.path.join(HARNESS_DIR, run_id)
        os.makedirs(run_dir, exist_ok=True)

        self.bs_via = opts['bs_via']
        servers, sides, worktree = self.make_sides(opts)
        store = browser.BrowserStore(HAR_PATH, mode, meta['session'])
        run = {
            'id': run_id, 'mode': mode, 'frozen_at': meta['recorded_at'],
            'widths': widths, 'modes': modes, 'notes': notes,
            'sides': [s.name for s in sides],
            'side_labels': {s.name: s.label for s in sides},
            'pages': [dict(p.__dict__, url=p.url) for p in pages],
            'shots': [], 'perf_requests': PERF_REQUESTS,
        }
        try:
            for server in servers:
                self.start_server(server, run_dir, mode, meta)
            if opts['record']:
                self.warm_check_urls(sides)
            if opts['html_only']:
                run['html'] = self.html_pass(pages, sides, token, run_dir)
            else:
                run['shots'], gz = asyncio.run(self.browser_pass(
                    pages, sides, widths, modes, token, store, run_dir, meta, opts))
                self.mark_identical(run['shots'])
                if opts['perf']:
                    run['perf'] = gz
            if opts['perf']:
                self.render_times(pages, sides, token, run.setdefault('perf', {}))
        finally:
            for server in servers:
                self.stop_server(server)
            store.save()
            if worktree:
                subprocess.run(['git', '-C', REPO_ROOT, 'worktree', 'remove', '--force', worktree],
                               check=False, capture_output=True)

        missing = self.missing_fixtures(servers)
        if missing:
            run['notes'].append('Missing API fixtures (re-record with --record): ' + '; '.join(sorted(missing)))
        if store.misses:
            run['notes'].append('%d browser requests had no recording and were aborted: %s' % (
                len(store.misses), '; '.join(sorted(store.misses)[:10])))
        run['checks'] = self.load_checks()
        run['wall_seconds'] = time.monotonic() - started
        with open(os.path.join(run_dir, 'run.json'), 'w') as f:
            json.dump(run, f, indent=1)
        with open(os.path.join(run_dir, 'index.html'), 'w') as f:
            f.write(sheet.render(run))
        self.report(run, run_dir)

    # Fixtures and sides -------------------------------------------------

    def session_meta(self, record):
        if record:
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            meta = {'recorded_at': now, 'session': now}
            os.makedirs(FIXTURES_DIR, exist_ok=True)
            with open(META_PATH, 'w') as f:
                json.dump(meta, f)
            return meta
        if not os.path.exists(META_PATH):
            raise CommandError('No recording in %s. Run: python manage.py shoot --record' % FIXTURES_DIR)
        with open(META_PATH) as f:
            return json.load(f)

    def make_sides(self, opts):
        has_ref = bool(opts['ref'])
        bs = opts['bs'] if opts['bs'] is not None else ('' if has_ref else '3,5')
        values = [v.strip() for v in bs.split(',')] if bs else ['']
        values = [('' if v == 'none' else v) for v in values]
        if len(values) == 1:
            values = values * 2
        if len(values) != 2:
            raise CommandError('--bs takes one value or two, before and after.')
        via = opts['bs_via']

        def label(where, value):
            return where + ('' if not value else ' (bs=%s %s)' % (value, via))

        here = Server('here', REPO_ROOT, 'microweb.visual_settings')
        after = Side('after', here, values[1], label('this checkout', values[1]))
        if not has_ref:
            # One server renders both sides; only the bs value differs.
            before = Side('before', here, values[0], label('this checkout', values[0]))
            return [here], [before, after], None
        sha = subprocess.run(['git', '-C', REPO_ROOT, 'rev-parse', '--short', opts['ref']],
                             capture_output=True, text=True)
        if sha.returncode:
            raise CommandError('Unknown git ref %r' % opts['ref'])
        worktree = tempfile.mkdtemp(prefix='microweb-harness-ref-')
        os.rmdir(worktree)
        subprocess.run(['git', '-C', REPO_ROOT, 'worktree', 'add', '--detach', worktree, opts['ref']],
                       check=True, capture_output=True)
        shutil.copy(os.path.join(settings.PROJECT_ROOT, 'local_settings.py'),
                    os.path.join(worktree, 'microweb', 'local_settings.py'))
        # The ref may predate the harness: serve.py brings the recorder.
        ref = Server('ref', worktree, 'microweb.settings')
        before = Side('before', ref, values[0], label('%s %s' % (opts['ref'], sha.stdout.strip()), values[0]))
        return [ref, here], [before, after], worktree

    def start_server(self, server, run_dir, mode, meta):
        server.port = free_port()
        server.log_path = os.path.join(run_dir, 'server-%s.log' % server.name)
        env = dict(os.environ, HARNESS_FIXTURES=FIXTURES_DIR, HARNESS_MODE=mode, HARNESS_SESSION=meta['session'])
        env.pop('HARNESS_TOKEN', None)
        with open(server.log_path, 'w') as log:
            server.proc = subprocess.Popen(
                [sys.executable, SERVE_SCRIPT, '--root', server.tree, '--port', str(server.port),
                 '--freeze', meta['recorded_at'], '--settings', server.settings_module],
                stdout=log, stderr=subprocess.STDOUT, env=env, cwd=server.tree)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if server.proc.poll() is not None:
                raise CommandError('Harness server %s exited; see %s' % (server.name, server.log_path))
            try:
                socket.create_connection(('127.0.0.1', server.port), timeout=1).close()
                return
            except OSError:
                time.sleep(0.2)
        raise CommandError('Harness server %s did not start; see %s' % (server.name, server.log_path))

    def stop_server(self, server):
        if server.proc and server.proc.poll() is None:
            server.proc.terminate()
            try:
                server.proc.wait(10)
            except subprocess.TimeoutExpired:
                server.proc.kill()

    def missing_fixtures(self, servers):
        missing = set()
        for server in servers:
            if server.log_path and os.path.exists(server.log_path):
                with open(server.log_path, errors='replace') as f:
                    for line in f:
                        m = re.search(r"FixtureMissingError: No recorded API fixture for '([^']+)'", line)
                        if m:
                            missing.add(m.group(1))
        return missing

    def load_checks(self):
        if os.path.exists(CHECKS_PATH):
            with open(CHECKS_PATH) as f:
                return json.load(f)
        return None

    # Requests -----------------------------------------------------------

    def cookies(self, side, page, token, mode='light'):
        """The cookies a request for `page` carries on `side`, as (name, value)."""
        out = []
        if side.bs and self.bs_via == 'cookie':
            out.append(('bs', side.bs))
        if mode == 'dark':
            out.append(('color_mode', 'dark'))
        if page is not None and page.signed_in:
            out.append(('access_token', token))
        return out

    def get(self, side, host, path, cookies):
        """GET a page from the side's server without a browser."""
        headers = {'Cookie': '; '.join('%s=%s' % c for c in cookies)} if cookies else {}
        return browser.forward_to_server(side.port, host, 'GET', self.page_path(path, side), headers)

    def page_path(self, path, side):
        if side.bs and self.bs_via == 'query':
            return path + ('&' if '?' in path else '?') + 'bs=' + side.bs
        return path

    def warm_check_urls(self, sides):
        for url in manifest.CHECK_URLS:
            parts = urlsplit(url)
            for side in sides:
                self.get(side, parts.hostname, parts.path + ('?' + parts.query if parts.query else ''),
                         self.cookies(side, None, None))

    def html_pass(self, pages, sides, token, run_dir):
        results = {}
        for page in pages:
            bodies = []
            for side in sides:
                _, _, body = self.get(side, page.host, page.path, self.cookies(side, page, token))
                # CSRF tokens are random per request; mask them so equal pages compare equal.
                body = CSRF.sub('CSRF', body.decode('utf-8', 'replace')).encode('utf-8')
                out = os.path.join(run_dir, 'html', side.name, page.label + '.html')
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, 'wb') as f:
                    f.write(body)
                bodies.append(body)
            results[page.label] = {'bytes': [len(b) for b in bodies], 'identical': bodies[0] == bodies[-1]}
        return results

    def render_times(self, pages, sides, token, perf):
        for page in pages:
            for side in sides:
                cookies = self.cookies(side, page, token)
                self.get(side, page.host, page.path, cookies)  # warm the Site cache
                times = []
                for _ in range(PERF_REQUESTS):
                    t = time.perf_counter()
                    self.get(side, page.host, page.path, cookies)
                    times.append((time.perf_counter() - t) * 1000)
                perf.setdefault(page.label, {}).setdefault(side.name, {})['render_ms'] = statistics.median(times)

    # Browser -----------------------------------------------------------

    async def browser_pass(self, pages, sides, widths, modes, token, store, run_dir, meta, opts):
        from playwright.async_api import async_playwright

        frozen = datetime.fromisoformat(meta['recorded_at'].replace('Z', '+00:00'))
        hosts = manifest.site_hosts()
        tasks = [(page, width, mode, side)
                 for page in pages for width in widths for mode in modes for side in sides]
        shots, gz = [], {}
        queue = asyncio.Queue()
        for t in tasks:
            queue.put_nowait(t)

        async with async_playwright() as p:
            chromium = await p.chromium.launch(args=browser.LAUNCH_ARGS)
            ua = browser.user_agent(chromium.version)
            routers = {side.port: browser.Router({h: side.port for h in hosts}, store) for side in sides}

            async def shoot_one(page_def, width, mode, side):
                name = side.name
                shot = {'label': page_def.label, 'width': width, 'mode': mode, 'side': name}
                t0 = time.monotonic()
                ctx = await chromium.new_context(
                    viewport={'width': width, 'height': VIEWPORT_HEIGHT}, device_scale_factor=1,
                    color_scheme=mode, reduced_motion='reduce', user_agent=ua)
                try:
                    await ctx.clock.set_fixed_time(frozen)
                    cookies = self.cookies(side, page_def, token, mode)
                    if cookies:
                        await ctx.add_cookies([{'name': n, 'value': v, 'url': 'https://%s/' % page_def.host}
                                               for n, v in cookies])
                    await ctx.route('**/*', browser.async_handler(routers[side.port]))
                    page = await ctx.new_page()
                    assets = []
                    collect = opts['perf'] and width == 1280 and mode == modes[0]
                    if collect:
                        page.on('response', lambda r: assets.append(r)
                                if r.request.resource_type in ('stylesheet', 'script') else None)
                    url = 'https://%s%s' % (page_def.host, self.page_path(page_def.path, side))
                    resp = await page.goto(url, wait_until='load', timeout=60000)
                    shot['status'] = resp.status if resp else None
                    await page.evaluate(SETTLE_JS)
                    await page.wait_for_timeout(opts['settle'])
                    if page_def.action == 'modal-signin':
                        await page.locator('[data-target="#modal-signin"], [data-bs-target="#modal-signin"]').first.click()
                        await page.wait_for_timeout(800)
                    shot.update(await page.evaluate(METRICS_JS, page_def.rows or None))
                    rel = os.path.join('shots', page_def.label, '%d-%s-%s.png' % (width, mode, name))
                    path = os.path.join(run_dir, rel)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    await page.screenshot(path=path, full_page=page_def.action != 'modal-signin',
                                          animations='disabled', caret='hide')
                    with open(path, 'rb') as f:
                        shot['sha256'] = hashlib.sha256(f.read()).hexdigest()
                    shot['file'] = rel
                    if collect:
                        total = 0
                        for r in {a.url: a for a in assets}.values():
                            try:
                                total += len(gzip.compress(await r.body(), 6))
                            except Exception:
                                pass
                        gz.setdefault(page_def.label, {}).setdefault(name, {})['gzip_bytes'] = total
                except Exception as e:
                    shot['error'] = str(e).split('\n')[0]
                finally:
                    await ctx.close()
                shot['seconds'] = round(time.monotonic() - t0, 2)
                self.stdout.write('%-20s %5d %-5s %-6s %s %.1fs' % (
                    page_def.label, width, mode, name, shot.get('status', shot.get('error')), shot['seconds']))
                shots.append(shot)

            async def worker():
                while True:
                    try:
                        t = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    await shoot_one(*t)

            await asyncio.gather(*[worker() for _ in range(max(1, opts['concurrency']))])
            await chromium.close()
        order = {(p.label, w, m, side.name): i for i, (p, w, m, side) in enumerate(tasks)}
        shots.sort(key=lambda s: order[(s['label'], s['width'], s['mode'], s['side'])])
        return shots, gz

    def mark_identical(self, shots):
        by_cell = {}
        for s in shots:
            by_cell.setdefault((s['label'], s['width'], s['mode']), {})[s['side']] = s
        for cell in by_cell.values():
            a, b = cell.get('before', {}), cell.get('after', {})
            same = bool(a.get('sha256')) and a.get('sha256') == b.get('sha256')
            for s in cell.values():
                s['identical'] = same

    def report(self, run, run_dir):
        shots = run['shots']
        errors = [s for s in shots if s.get('error')]
        n_pages = len(run['pages'])
        self.stdout.write('')
        for note in run['notes']:
            self.stdout.write(note)
        if shots:
            same = sum(1 for s in shots if s['identical'] and s['side'] == 'before')
            self.stdout.write('%d shots, %d errors, %d/%d cells identical before/after.' % (
                len(shots), len(errors), same, len(shots) // 2))
        self.stdout.write('Wall time %.1f s for %d pages (%.1f s per page).' % (
            run['wall_seconds'], n_pages, run['wall_seconds'] / max(1, n_pages)))
        self.stdout.write('Contact sheet: %s' % os.path.join(run_dir, 'index.html'))
