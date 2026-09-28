"""Browser-side plumbing shared by `manage.py shoot` and the browser checks.

Live Sites sit behind a Cloudflare challenge that blocks headless Chromium,
so the browser never loads a live Site. Every request is routed:

- A Site host (from the manifest) goes to the local harness server, with the
  Host header preserved, so the page renders exactly as that Site.
- Any other GET from the top frame (API images, fonts, Site backgrounds,
  scripts on other hosts) is recorded to and replayed from a HAR file.
  Recording fetches with a plain HTTP client, not the browser. Legacy
  `*.microco.sm` URLs, which never answer, are fetched from `*.microcosm.app`.
  Animated GIFs are served as their first frame.
- An embedded iframe from another host gets a flat placeholder, so embeds
  (YouTube, Instagram, maps tiles in frames) cannot make shots flaky.
- Everything else is aborted.

The request-resolving code is synchronous and API-agnostic; `async_handler`
and `sync_handler` adapt it to Playwright's async and sync APIs.
"""
import asyncio
import base64
import http.client
import json
import os
import re
import tempfile
import threading
from urllib.parse import urlsplit

import requests

RECORD = 'record'
REPLAY = 'replay'
NO_ANSWER = 0  # HAR status for a request whose host never answered

KEPT_HEADERS = ('content-type', 'location', 'access-control-allow-origin',
                'access-control-allow-credentials', 'access-control-allow-headers')
FORWARDED_HEADERS = ('user-agent', 'accept', 'accept-language', 'authorization', 'origin', 'referer')
HOP_HEADERS = ('content-length', 'transfer-encoding', 'connection', 'content-encoding', 'keep-alive')

LEGACY_HOST = re.compile(r'^https?://([^/]+)\.microco\.sm/')

PLACEHOLDER = (
    '<!doctype html><html><body style="margin:0;height:100vh;display:flex;'
    'align-items:center;justify-content:center;background:#dcdcdc;color:#555;'
    'font:13px/1.3 sans-serif">embed: %s</body></html>'
)


class BrowserStore(object):
    """Off-site browser responses, kept as a HAR 1.2 file."""

    def __init__(self, path, mode=REPLAY, session=''):
        self.path = path
        self.mode = mode
        self.session = session
        self.entries = {}
        self.misses = set()
        self._lock = threading.Lock()
        self._key_locks = {}
        self._dirty = False
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                for entry in json.load(f)['log']['entries']:
                    self.entries[(entry['request']['method'], entry['request']['url'])] = entry

    def lookup(self, method, url, headers):
        key = (method, url)
        if self.mode == REPLAY:
            entry = self.entries.get(key)
            if entry is None:
                self.misses.add('%s %s' % key)
                return None
            return _from_entry(entry)
        with self._lock:
            key_lock = self._key_locks.setdefault(key, threading.Lock())
        # One fetch per URL and session, however many pages ask at once.
        with key_lock:
            entry = self.entries.get(key)
            if entry is not None and entry.get('_session') == self.session:
                return _from_entry(entry)
            # A host that does not answer is recorded as status 0, so replay
            # aborts it too instead of reporting a missing recording.
            fetched = _fetch_external(url, headers) or (NO_ANSWER, {}, b'')
            with self._lock:
                self.entries[key] = entry = _to_entry(method, url, fetched, self.session)
                self._dirty = True
            return _from_entry(entry)

    def save(self):
        if not self._dirty:
            return
        har = {'log': {
            'version': '1.2',
            'creator': {'name': 'microweb-harness', 'version': '1'},
            'entries': [self.entries[k] for k in sorted(self.entries)],
        }}
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path), suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(har, f)
        os.replace(tmp, self.path)
        self._dirty = False


def _fetch_external(url, headers):
    fetch_url = LEGACY_HOST.sub(lambda m: 'https://%s.microcosm.app/' % m.group(1), url)
    sent = {k: v for k, v in headers.items() if k.lower() in FORWARDED_HEADERS}
    try:
        r = requests.get(fetch_url, headers=sent, timeout=30)
    except requests.RequestException:
        return None
    kept = {k.lower(): v for k, v in r.headers.items() if k.lower() in KEPT_HEADERS}
    return r.status_code, kept, r.content


def _to_entry(method, url, fetched, session):
    status, headers, body = fetched
    return {
        '_session': session,
        'startedDateTime': session or '1970-01-01T00:00:00Z',
        'time': 0,
        'request': {'method': method, 'url': url, 'httpVersion': 'HTTP/1.1', 'headers': [],
                    'queryString': [], 'cookies': [], 'headersSize': -1, 'bodySize': 0},
        'response': {
            'status': status, 'statusText': '', 'httpVersion': 'HTTP/1.1',
            'headers': [{'name': k, 'value': v} for k, v in sorted(headers.items())],
            'cookies': [],
            'content': {'size': len(body), 'mimeType': headers.get('content-type', ''),
                        'text': base64.b64encode(body).decode('ascii'), 'encoding': 'base64'},
            'redirectURL': '', 'headersSize': -1, 'bodySize': len(body),
        },
        'cache': {},
        'timings': {'send': 0, 'wait': 0, 'receive': 0},
    }


def _from_entry(entry):
    response = entry['response']
    if response['status'] == NO_ANSWER:
        return None
    headers = {h['name']: h['value'] for h in response['headers']}
    return response['status'], headers, base64.b64decode(response['content']['text'])


def _skip_color_table(data, i, flags):
    return i + 3 * (2 ** ((flags & 7) + 1)) if flags & 0x80 else i


def _skip_sub_blocks(data, i):
    while data[i]:
        i += data[i] + 1
    return i + 1


def first_gif_frame(data):
    """Cut an animated GIF down to its first frame.

    Chromium plays GIFs on its own clock, so an animated avatar would land
    on a different frame in each shot. Anything that is not a GIF, or does
    not parse, comes back unchanged.
    """
    if data[:6] not in (b'GIF87a', b'GIF89a'):
        return data
    try:
        i = _skip_color_table(data, 13, data[10])
        while i < len(data):
            if data[i] == 0x21:  # extension: label, then sub-blocks
                i = _skip_sub_blocks(data, i + 2)
            elif data[i] == 0x2C:  # image: descriptor, colour table, LZW size, data
                i = _skip_color_table(data, i + 10, data[i + 9])
                i = _skip_sub_blocks(data, i + 1)
                return data[:i] + b'\x3b'
            else:
                return data
    except IndexError:
        pass
    return data


def forward_to_server(port, host, method, path, headers, body=None):
    """Send a browser request to the local harness server as `host`."""
    sent = {k: v for k, v in headers.items() if not k.startswith(':') and k.lower() not in ('host',) + HOP_HEADERS}
    sent['Host'] = host
    sent['X-Forwarded-Proto'] = 'https'
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=120)
    try:
        conn.request(method, path, body=body, headers=sent)
        r = conn.getresponse()
        data = r.read()
        # Repeated headers (Set-Cookie) are joined; fine for the harness.
        out = {}
        for k, v in r.getheaders():
            if k.lower() in HOP_HEADERS:
                continue
            out[k] = v if k not in out else out[k] + ('\n' if k.lower() == 'set-cookie' else ', ') + v
        return r.status, out, data
    finally:
        conn.close()


class Router(object):
    """Decides how each browser request is answered.

    `servers` maps a Site host to the local port that renders it.
    """

    def __init__(self, servers, store):
        self.servers = servers
        self.store = store

    def resolve(self, method, url, headers, body, is_subframe_navigation, from_subframe):
        """Return ('fulfill', status, headers, body) or ('abort',)."""
        parts = urlsplit(url)
        host = parts.hostname or ''
        path = parts.path or '/'
        if parts.query:
            path += '?' + parts.query
        port = self.servers.get(host)
        if port and not parts.path.startswith('/api/'):
            return ('fulfill',) + forward_to_server(port, host, method, path, headers, body)
        if is_subframe_navigation:
            return ('fulfill', 200, {'content-type': 'text/html'}, (PLACEHOLDER % host).encode('utf-8'))
        if from_subframe or method != 'GET':
            return ('abort',)
        found = self.store.lookup(method, url, headers)
        if found is None:
            return ('abort',)
        status, out, body = found
        return ('fulfill', status, out, first_gif_frame(body))


def _frame_facts(request):
    try:
        frame = request.frame
    except Exception:  # service worker requests have no frame
        return False, True
    subframe = frame.parent_frame is not None
    return subframe and request.is_navigation_request(), subframe


def async_handler(router):
    async def handle(route):
        request = route.request
        is_nav, from_subframe = _frame_facts(request)
        headers = await request.all_headers()
        outcome = await asyncio.to_thread(
            router.resolve, request.method, request.url, headers,
            request.post_data_buffer, is_nav, from_subframe)
        if outcome[0] == 'abort':
            await route.abort()
        else:
            _, status, out, body = outcome
            await route.fulfill(status=status, headers=out, body=body)
    return handle


def sync_handler(router):
    def handle(route):
        request = route.request
        is_nav, from_subframe = _frame_facts(request)
        outcome = router.resolve(request.method, request.url, request.all_headers(),
                                 request.post_data_buffer, is_nav, from_subframe)
        if outcome[0] == 'abort':
            route.abort()
        else:
            _, status, out, body = outcome
            route.fulfill(status=status, headers=out, body=body)
    return handle


# Chromium switches that take timing out of rasterisation, so one recording
# shoots to identical pixels: decode images before paint (checker imaging
# otherwise lands scaled avatars at different filter qualities), raster
# whole tiles, grayscale text, one colour profile.
LAUNCH_ARGS = [
    '--disable-checker-imaging',
    '--disable-partial-raster',
    '--disable-lcd-text',
    '--disable-threaded-animation',
    '--disable-threaded-scrolling',
    '--force-color-profile=srgb',
    '--hide-scrollbars',
    '--num-raster-threads=1',
]


def user_agent(browser_version):
    """A desktop Chrome user agent. 'HeadlessChrome' changes what some hosts
    (Google Fonts, Cloudflare) serve."""
    return ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/%s Safari/537.36' % browser_version)
