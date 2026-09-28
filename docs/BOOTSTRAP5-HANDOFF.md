# Bootstrap 5 migration handoff

This file starts a new planning session. It records what the previous session measured and decided, so the new session does not repeat that work. An earlier plan for owned CSS was written and then dropped when this requirement replaced it. Everything worth keeping from it is below.

## The requirement

Move Microweb from Bootstrap 3.0.3 to Bootstrap 5. Keep the look and design close to today's, but a pixel-exact match is not required. Keep the number of custom design tokens small, so that the site can offer several colour themes. The themes are light, dark, high contrast, and any others that Bootstrap supports. Stage the work so that each change is understandable. Simplicity for the people maintaining the repo counts as a feature, alongside modern web standards.

The earlier constraint "do not change the styling approach" no longer applies. Template class names and markup may change.

## Measured facts

These facts come from the working tree at `338d3c21` on `wip/theming` and from the npm registry on 2026-09-27.

**Current CSS.**

- `core/static/themes/1/css/theme.css` is 181,065 bytes and 10,873 lines, with no source files. Lines 1 to about 6070 are normalize.css 2.1.3 and compiled Bootstrap 3.0.3. The app's own rules follow, with the datepicker CSS from line 9953.
- Templates use 85 of the 391 Bootstrap 3 classes and 224 of the app's own classes. 306 Bootstrap classes and 80 app classes are never used.
- The app region has 293 colour declarations and 64 distinct colours. The same literal serves different roles. For example, `#ccc` is a border about 33 times and a text colour 11 times.
- `base.html` lines 22 to 60 hold the per-site theming. `theme.css` loads from `themes/{{ site.theme_id }}/`, and only `themes/1/` exists. An inline `#site-style` block sets `--link-color`, `--background-color`, and a background image with five position modes (`tile`, `cover`, `tall`, `wide`, and a named position). Auth0 Lock also gets `primaryColor: '{{ site.link_color }}'`.

**Current JavaScript.**

- `js/bootstrap.min.js` is 27,484 bytes and bundles the Stefan Petre datepicker after the Bootstrap 3 plugins. jQuery is 1.10.2.
- Templates hold 16 `data-toggle="modal"`, 11 `data-toggle="tooltip"`, 10 `data-dismiss="modal"`, one `data-toggle="dropdown"`, and one `data-toggle="collapse"`. Scripts call `.datepicker(` 9 times, `.tooltip(` 3 times, `.collapse(` twice, and `.modal(`, `.button(`, and `.textcomplete(` once each.
- Templates hold 254 uses of 30 distinct classes that Bootstrap 5 renames or drops. Examples are `btn-default` (52), `form-group`, `btn-xs` (20), `pull-right` (19), `has-error` (20), `control-label` (12), `col-xs-*`, `label`, `well`, and `input-group-addon`. The rename list came from memory of the Bootstrap 5 migration guide. Check it against the guide.

**Images.**

- `img/icons.png` and `icons@2x.png` are a raster sprite of grey glyphs and one orange envelope. 33 `sprite-*` names are in use.
- `themes/1/logo.png` is black text on transparency. `preloader.gif` is used in `forms/subscribe.html` and `huddle.html`.

**Dead files.** Nothing references these, so deleting them is safe.

- `js/eventTime.js`, `js/m-event.js`, `js/m-f-event.js`, `js/md5.min.js`, and `js/mozpersona.js`.
- `js/locales/`.
- `3rd/moment.js/2.0.0/`, `3rd/leaflet/1.0.0/`, `3rd/html5shiv/`, `3rd/respond.js/`, and `3rd/isogram/`.
- `themes/1/css/base.css` and `img/quote-marks.png`.

**Bootstrap 5 today.**

- `npm view bootstrap dist-tags` gives `latest: 5.3.8`. No Bootstrap 6 is published. `bootstrap-icons` is at 1.13.1.
- The compiled `dist/css/bootstrap.min.css` is 232,111 bytes, or 31,078 bytes gzip.
- It ships two colour modes, `[data-bs-theme=light]` and `[data-bs-theme=dark]`. It has no high-contrast mode, and it has no `prefers-contrast` or `forced-colors` rules.
- Compiled component colours are literal. `.btn-primary` sets `--bs-btn-bg:#0d6efd` and its hover and active shades as hex. Overriding `--bs-primary` at runtime does not recolour buttons. Recolouring them needs either a Sass build or per-component variable overrides in each theme.
- Links read `color: rgba(var(--bs-link-color-rgb), var(--bs-link-opacity,1))`. A per-site link colour therefore has to reach the page as an RGB triple, such as `64,130,195`, not as hex.

## Carry over from the previous session

- **Screenshot harness design.** The earlier plan designed a harness to compare pages before and after a change. Keep the design, but use it to produce side-by-side images for review, not to fail on any pixel difference.
  - Every API call in `core/api/resources.py` and `core/api/fetch.py` goes through `requests`. One wrapper on `requests.adapters.HTTPAdapter.send` can record API responses to JSON files and replay them, keyed by method, URL, sorted query, and whether an access token was present. Install it from a `CoreConfig.ready()` only when a dev-only setting is present, and load that setting from a `microweb/visual_settings.py` that also swaps memcached for `LocMemCache`.
  - Freeze server time, for example with `freezegun`, so the six `|timesince` filters render the same text on every run.
  - `lfgss.com` and `*.microcosm.app` are HSTS-preloaded, so browsers insist on HTTPS. The untracked `Caddyfile.dev` terminates TLS for `www.lfgss.com` on 127.0.0.1 and proxies to runserver on port 8000. Playwright maps the host with `--host-resolver-rules` and replays fonts, avatars, and map tiles from a HAR file.
  - Shoot each page at 375, 768, and 1280 pixels wide, once per theme, in Chromium, Firefox, and WebKit. Compare two git refs by checking each out into a worktree and running them one after the other on the same port.
  - Keep a class census script. The earlier session's version parsed `theme.css`, split it at line 6070, and counted class use in templates and app scripts. It found the 85, 224, 306, and 80 counts above.
- **Subtract first.** S1's deletions stand as written.
- **Site overrides must not be unlayered rules.** The inline `#site-style` block writes rules such as `a { color: var(--link-color) }` outside any cascade layer or theme scope, so they beat theme rules. Cut it to variables only, and let the theme CSS decide how to use them. Under Bootstrap 5, the site link colour maps onto `--bs-link-color-rgb` and `--bs-link-hover-color-rgb`, and the site background onto `--bs-body-bg` or the body rule. A dark theme must be able to adjust the link colour for contrast, for example with `color-mix()`.
- **Auth0 Lock inside a modal.** The **Sign in** button in `#modal-signin` (`modal_signin.html:14`) calls `authSignin()`. Lock mounts its overlay on `<body>`. Any modal that traps focus or makes the rest of the page inert blocks Lock. That includes a native `<dialog>` opened with `showModal()`. From memory, Bootstrap 5's modal also pulls focus back into itself, so it probably blocks Lock too. That is an inference, not a test. Close the modal before calling Lock, and test the flow.
- **Datepicker.** Replace it with `<input type="date">`. Record the date format that `eventFormClasses.js` sends and the event form in `events/` parses before changing either.
- **Icons.** Bootstrap Icons is the natural replacement for the PNG sprite. As inline SVG or SVG masks, the icons take `currentColor` in every theme.
- **Leaflet 0.7.7 and Auth0 Lock 2.2.3** have no dark theme. Pin them to `color-scheme: light`.
- **jQuery removal is a separate program.** Bootstrap 5 does not need jQuery. The app's scripts and 46 inline `$(` calls still do. The outline has four steps. First, port `base.js`, `metabar.js`, `comments.js`, `filters.js`, `attachments.js`, `profilePicture.js`, `formValidator.js`, `simpleEditor.js`, and the inline template calls. Second, port `eventForm.js`, `eventFormClasses.js`, `peopleWidget.js`, and `membership_form.js`. Third, replace `jquery.textcomplete` for mentions. Fourth, delete jQuery. Moment.js 2.10.6 can then give way to `Intl.DateTimeFormat` and `Intl.RelativeTimeFormat`.

## Settle these first

Settle each one with a prototype or a measurement before writing the plan. Each is a fact the new session can observe.

1. **How old and new CSS coexist during the migration.** A page cannot load Bootstrap 3 and Bootstrap 5 together without conflicts. Shared includes such as `block_*.html` and `modal_*.html` render inside many pages. The options are a per-template switch in `base.html` (`{% block framework %}`), one long-lived branch with staged commits, or migrating shared includes first. Staged, reviewable PRs are a requirement, so this choice shapes the whole plan.
2. **Sass build or compiled CSS.** A Sass build lets a theme set a few variables (`$primary`, `$body-bg`, fonts) and generates every component shade. It adds a toolchain, for example the standalone `dart-sass` binary in a Docker build stage. The project has no Node or Sass build today, and its dependencies are pure Python. Compiled CSS needs no build, but each theme must override component variables such as `--bs-btn-bg`. Build one theme both ways and count the lines a maintainer would own.
3. **The theme set and its mechanism.** Light and dark come built in. High contrast is custom. Decide whether it is a third `data-bs-theme` value, a `prefers-contrast: more` media query, or both. Then decide how the theme is chosen. The choices are the system setting, a member toggle (a cookie that `ContextMiddleware` reads and renders as `data-bs-theme` on `<html>`, so the page does not flash), or per site. Decide whether `site.theme_id` keeps its meaning.
4. **Clean room or codemod.** A codemod renames classes mechanically, such as `btn-default` to `btn-secondary` and `pull-right` to `float-end`. It keeps the 224 app classes that were tuned to Bootstrap 3 metrics. A clean-room rewrite rebuilds each template family with Bootstrap 5 components and utilities, and deletes app CSS that Bootstrap now covers. That is the path that shrinks the custom token count. Prototype one family both ways, such as the conversation page, and compare how much app CSS survives.
5. **How close is close enough.** Pick a reference set of pages at 375 and 1280 pixels wide in the old design. Agree with the operator on what may change, such as spacing scale, font sizes, form control look, and focus rings, and what may not, such as colours, the site background, the logo, and layout.

## Suggested stages

Treat this outline as a starting point for the new plan, not a decision.

1. Build the screenshot harness and delete dead files.
2. Replace the site-override block with variables and add the theme mechanism, still on Bootstrap 3.
3. Bring in Bootstrap 5 with the coexistence approach from question 1, and migrate `base.html`, the navbar, and the footer.
4. Migrate one template family per PR. The families are lists (`home`, `microcosm`, `updates`), conversations and comments, events, profiles, forms, huddles, and modals.
5. Replace the datepicker, icons, and the remaining plugin calls.
6. Delete Bootstrap 3 CSS and JavaScript and the app CSS that no template uses.
7. Add dark and high-contrast themes, each as a small tokens change, and review screenshots of both.

## Environment notes

- Claude Code here has no `control-ui`, `deslop`, or `poteto-agent`. Drive browsers with Playwright scripts, use `/simplify` for cleanup, and use `general-purpose` subagents on `opus`, `sonnet`, or `fable`.
- `~/.claude/skills/poteto-mode/scripts/check-plan.mjs` lints a plan written to the multi-phase template.
- Fixtures recorded from lfgss hold member content and the operator's private huddles. Keep them out of git.
- The `origin` remote is `microcosm-collective/microweb`. The `fork` remote is `duncanhope/microweb`.
