"""Record and replay the Microcosm API calls Django makes.

Wraps requests.adapters.HTTPAdapter.send, so every API call (fetch.map,
APIResource helpers, CNAME lookups) passes through it, redirect hops
included. A call is keyed by method, URL without query, sorted query, and
whether an Authorization header was present. The token itself never reaches
the key or the fixture.

Modes:
  record  fetch from the network and write a fixture. Within one recording
          session (HARNESS_SESSION) a key already written is served from disk,
          so every page and both sides of a comparison see the same data.
  replay  serve fixtures only; a missing key raises FixtureMissingError.

This module only imports the standard library, requests and urllib3: the
harness loads it by file path into servers running other git refs.
"""
import base64
import hashlib
import io
import json
import os
import tempfile
import threading
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from requests.adapters import HTTPAdapter
from urllib3.response import HTTPResponse

RECORD = 'record'
REPLAY = 'replay'

# Headers worth replaying. Everything else (cookies, encodings, lengths,
# Cloudflare noise) is dropped so fixtures stay small and replay is exact.
KEPT_HEADERS = ('content-type', 'location')


class FixtureMissingError(RuntimeError):
    """Replay found no recording for an API call.

    Deliberately not a requests.RequestException: fetch._send would turn
    that into a silent None and the page would render an error state. This
    propagates as a 500 with the key in the server log.
    """


def request_key(method, url, headers=None):
    parts = urlsplit(url)
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    base = urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))
    auth = 'auth' if headers and 'Authorization' in headers else 'anon'
    key = '%s %s' % (method.upper(), base)
    if query:
        key += '?' + query
    return key + ' ' + auth


def fixture_name(key):
    return hashlib.sha256(key.encode('utf-8')).hexdigest()[:24] + '.json'


class Recorder(object):

    def __init__(self, fixtures_dir, mode=REPLAY, session=''):
        if mode not in (RECORD, REPLAY):
            raise ValueError('Recorder mode must be %r or %r, not %r' % (RECORD, REPLAY, mode))
        self.dir = os.path.join(fixtures_dir, 'api')
        self.mode = mode
        self.session = session
        self._lock = threading.Lock()
        self._key_locks = {}
        self._original = None

    def path_for(self, key):
        return os.path.join(self.dir, fixture_name(key))

    def load(self, key):
        try:
            with open(self.path_for(key), encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save(self, key, response):
        body = response.content
        try:
            text, encoding = body.decode('utf-8'), 'utf-8'
        except UnicodeDecodeError:
            text, encoding = base64.b64encode(body).decode('ascii'), 'base64'
        record = {
            'key': key,
            'session': self.session,
            'status': response.status_code,
            'reason': response.reason,
            'headers': {k.lower(): v for k, v in response.headers.items() if k.lower() in KEPT_HEADERS},
            'encoding': encoding,
            'body': text,
        }
        os.makedirs(self.dir, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.dir, suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path_for(key))
        return record

    def build_response(self, adapter, request, record):
        body = record['body'].encode('utf-8')
        if record['encoding'] == 'base64':
            body = base64.b64decode(body)
        raw = HTTPResponse(
            body=io.BytesIO(body),
            headers=record['headers'],
            status=record['status'],
            reason=record.get('reason'),
            preload_content=False,
            decode_content=False,
        )
        return adapter.build_response(request, raw)

    def send(self, adapter, request, **kwargs):
        key = request_key(request.method, request.url, request.headers)
        if self.mode == REPLAY:
            record = self.load(key)
            if record is None:
                raise FixtureMissingError(
                    'No recorded API fixture for %r (looked for %s). '
                    'Record it with: python manage.py shoot --record' % (key, self.path_for(key)))
            return self.build_response(adapter, request, record)
        # One network fetch per key and session, even when both sides of a
        # comparison ask at once.
        with self._key_lock(key):
            record = self.load(key)
            if record is not None and self.session and record.get('session') == self.session:
                return self.build_response(adapter, request, record)
            response = self._original(adapter, request, **kwargs)
            self.save(key, response)
            return response

    def _key_lock(self, key):
        with self._lock:
            return self._key_locks.setdefault(key, threading.Lock())

    def install(self):
        if self._original is not None:
            return self
        self._original = HTTPAdapter.send
        recorder = self

        def send(adapter, request, *args, **kwargs):
            return recorder.send(adapter, request, **_send_kwargs(args, kwargs))

        send.harness_recorder = self
        HTTPAdapter.send = send
        return self

    def uninstall(self):
        if self._original is not None:
            HTTPAdapter.send = self._original
            self._original = None


def _send_kwargs(args, kwargs):
    names = ('stream', 'timeout', 'verify', 'cert', 'proxies')
    merged = dict(zip(names, args))
    merged.update(kwargs)
    return merged


def installed():
    """The Recorder currently wrapping HTTPAdapter.send, or None."""
    current = getattr(HTTPAdapter.send, 'harness_recorder', None)
    return current if isinstance(current, Recorder) else None


def install(fixtures_dir, mode=REPLAY, session=''):
    current = installed()
    if current is not None:
        current.uninstall()
    return Recorder(fixtures_dir, mode, session).install()
