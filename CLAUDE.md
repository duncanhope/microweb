# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Microweb is the Django web client for [Microco.sm](http://microcosm.app), a forum SaaS. **It has no database** — all content (conversations, events, comments, profiles, sites) lives behind the Microcosm REST API. Microweb is essentially a server-rendered HTML front end that translates HTTP requests into API calls and renders the responses. `DATABASES = {}` in settings; app tests subclass `SimpleTestCase` because there is nothing to migrate or flush.

The stack is **Python 3.12+ (3.14 in production) / Django 6.0**. Dependencies are pure Python (no C extensions).

## Commands

Setup:

```bash
python3 -m venv ENV
source ENV/bin/activate
pip install -r requirements.txt
```

Before running anything you must create `microweb/local_settings.py` from `microweb/local_settings.py.sample` (it holds the API client credentials and API host). A local memcached on port 11211 is required at runtime (site/CNAME cache), though not for the unit tests.

```bash
# Run the dev server (set DEBUG=True in local_settings.py so static files are served)
python manage.py runserver

# Or serve https://www.lfgss.com locally as production does (Caddy for TLS,
# gunicorn, memcached), against the API in local_settings.py; one-time
# setup (hosts entries, trusting Caddy's CA, setcap) is in the script header
bin/serve-local

# Run all unit tests
python manage.py test

# Run tests for a single app / case / method
python manage.py test conversations
python manage.py test core.tests.tests.SomeTestCase
python manage.py test core.tests.tests.SomeTestCase.test_something

# CI runs tests with a dedicated settings module (no local_settings.py needed)
python manage.py test --settings=microweb.travis_settings
```

There is also a separate [selenium integration suite](https://github.com/microcosm-collective/microweb-selenium-tests) that runs as a standalone process against a live instance.

## Architecture

### One Django app per API resource type

Each top-level directory (`conversations`, `events`, `huddles`, `microcosms`, `comments`, `profiles`, `updates`, `search`, `trending`, `moderation`, `redirect`, `today`, `ignored`) is a Django app holding the `urls.py` and `views.py` for that resource. `models.py` files are empty stubs — there is no ORM. `core` is shared infrastructure: the API client, middleware, forms, templates, templatetags, and error views.

URL routing is flat: `microweb/urls.py` includes every app's urls at the root (`r''`) using `re_path` (deliberately not `path()` — several patterns are unanchored regexes). **`redirect.urls` MUST stay last** — it catches everything else as a potential 404 / API-driven redirect.

### The API client: `core/api/resources.py`

This single large file is the heart of the app. Each API resource has a class (`Conversation`, `Event`, `Microcosm`, `Profile`, `Comment`, `Site`, `WhoAmI`, etc.), most subclassing `APIResource`. The conventional methods on each class:

- `build_request(host, ...)` → returns `(url, params, headers)` **without** making the call. This is what lets views batch requests (see below).
- `retrieve` / `create` / `update` / `delete` — synchronous calls that go through `APIResource`'s static HTTP helpers. Note `update` POSTs with a `method=PUT` query param rather than using a real PUT verb.
- `from_api_response(cls, data)` / `from_summary` — build a Python object from parsed JSON.
- `from_create_form` / `from_edit_form` — build an API payload from a validated Django form.

`APIResource.process_response` enforces the API envelope: every response is `{error, data}`; a non-empty `error` raises `APIException` (from `core/api/exceptions.py`), and views catch it and call `respond_with_error`.

### Concurrent requests via core/api/fetch.py

Views batch their API calls and execute them concurrently on a shared `concurrent.futures.ThreadPoolExecutor` (one per gunicorn worker process). The request flow:

1. `ContextMiddleware` (`core/middleware/context.py`) runs on every request. It reads the `access_token` cookie (auth is entirely the API's job — there is no Django auth) and seeds `request.view_requests`, a list of pending `fetch.get(...)` descriptors. It always queues a `Site` lookup, and a `WhoAmI` lookup if logged in.
2. A view appends its own resource `build_request(...)` calls as `fetch.get(url, params, headers)` descriptors to `request.view_requests`.
3. The view fires them all concurrently with `fetch.map(request.view_requests)` and converts the result with `response_list_to_dict`, which keys responses **by request URL** (following one redirect, e.g. `/whoami` → `/profiles/{id}`). A failed request maps to `None` and is skipped.
4. The view pulls each response out of that dict by URL, hydrates resource objects, and renders a template.

`conversations/views.py:single` is the canonical example to copy when writing a new view. `fetch._send` calls `requests.get` by module attribute, so tests can keep patching `'requests.get'`.

### Custom-domain (CNAME) resolution

Customers CNAME their own domain to a Microcosm site, so `ALLOWED_HOSTS = ['*']` and the host is validated by the API instead. In `build_url`/`get_subdomain_url` (`resources.py`), any host not ending in the API domain is resolved to its real site via the API `/hosts` endpoint, with results cached in **memcached** via `django.core.cache` (PyMemcacheCache backend, `ignore_exc` so a memcached outage degrades to cache misses). The cache client is imported as `mc` in `resources.py` — tests patch `core.api.resources.mc`. Unresolvable hosts are negative-cached for a day (`NEGATIVE_CNAME_CACHE_VALUE`); IP-address hosts are refused outright.

### Middleware

All middleware is new-style callable classes (`__init__(self, get_response)` / `__call__`), but each keeps its logic in a `process_request`/`process_response` method for direct testability. Ordering in settings matters: `PreconnectMiddleware`/`CorsMiddleware` sit **above** `ContextMiddleware`/`DomainRedirectMiddleware` so that short-circuited responses (e.g. 404 for unknown hosts) still get their headers.

### Settings layering

`microweb/settings.py` holds non-secret defaults and imports secrets/overrides from `microweb/local_settings.py` (gitignored). `local_settings.py.sample` is the dev template; `local_settings.py.production` is copied into place by the `Dockerfile`. Production reads most values from environment variables (API host, memcache host, secret key). `CACHES` is defined at the bottom of `settings.py` because it depends on the late `local_settings` imports.

## Deployment

Production deploys via **Dokku** (Docker under the hood) by pushing to a git remote — see `DEPLOYMENT.md` for the full server setup. The `Dockerfile` is `python:3.14-slim` and runs `gunicorn` with gthread workers (4 workers × 8 threads); each worker process owns one fetch executor. Static files are collected at image build time and served by `whitenoise` (wired as the first middleware).
