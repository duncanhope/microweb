# Bootstrap 5 migration plan

Microweb moves from Bootstrap 3.0.3 and jQuery to Bootstrap 5.3.8 with light and dark Color modes, one deployable PR at a time. Visitors see nothing until the flip, except the operator and opted-in members using the `bs` preview cookie. The rule is clean room per template family, `--bs-*` variables only, and no new jQuery. The PRs run in this order.

BS5-01, BS5-02, BS5-03, BS5-04, BS5-05, BS5-06, BS5-07, BS5-08, BS5-09, BS5-10, BS5-11, BS5-12, BS5-13, BS5-14, BS5-15, BS5-16, BS5-17, BS5-18.

## How to read this

One box is one unit of work. Every box names the evidence that checks it. A nested box is a sub-step of the box above it. Check a box only when its evidence exists, a file, a log line, a screenshot, a test run, or a SHA. The body is a how-to. The appendices explain and record.

The program runs `~/.claude/skills/poteto-mode/playbooks/autopilot-stack.md`, because the work is sequenced and the operator lands every PR. Work stays local. Each PR is a feature branch `bs5/<pr-id>-<slug>` cut from local `main`, and trunk means local `main`. The operator reviews each branch and merges it into local `main` in order. Nothing is pushed to `origin`, and the operator pushes to `fork` by hand. BS5-16 waits on the operator's flip decision, and BS5-17 waits about two weeks after the flip.

This repo has no `swarm`, `control-ui` or cloud VMs. Owners are Claude Code `general-purpose` subagents in worktrees. Live lanes are subagents on `sonnet` that drive the Playwright harness from BS5-02. Before BS5-02 lands, BS5-01 uses the throwaway `capture.mjs` from `research/before-screenshots`. Every decision cited here lives in a ticket under `.scratch/bootstrap5/issues/`, indexed by `.scratch/bootstrap5/map.md`.

Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

## Program checklist

### Arm the program

- [ ] State the protocol and this plan to the operator, then stop. Start execution only on the operator's explicit go.
- [ ] On the operator's go, arm a `/goal` with this exact text. "Execute docs/bootstrap5-plan.md, PRs BS5-01 then BS5-02 then BS5-03 then BS5-04 then BS5-05 then BS5-06 then BS5-07 then BS5-08 then BS5-09 then BS5-10 then BS5-11 then BS5-12 then BS5-13 then BS5-14 then BS5-15 then BS5-16 then BS5-17 then BS5-18. Tests alone are not sufficient verification, a PR is verified only when its unit, live, and perf boxes are all checked. The operator reviews every branch and merges it into local main. Nothing is pushed to origin. Done when BS5-18 is merged into local main and every box is checked."
- [ ] Read these from local `main` at program start. Re-read them at every tick. The template's `git show origin/main:` reads become `git show main:` here, because nothing is pushed to `origin`.
  - [ ] `git show main:docs/bootstrap5-plan.md`
  - [ ] `git show main:CLAUDE.md`
  - [ ] `git show main:CONTEXT.md`
  - [ ] `cat ~/.claude/skills/poteto-mode/playbooks/autopilot-stack.md` and `playbooks/opening-a-pr.md`, which live outside the repo.
  - [ ] The decision tickets under `.scratch/bootstrap5/issues/` for the PR in hand.
- [ ] Arm the 30-minute audit tick with a real terminal `/loop`.
- [ ] Use this tick prompt, verbatim. "Re-read the execution playbook from trunk and the armed /goal. Audit the operation against both and fix drift in this tick. Probe every active lane and judge progress by side effects only. Stand down a stuck lane and dispatch its replacement now. Then post a short status message to the operator in chat only when the audit found a tracked change that no earlier status message reported, such as a PR opened, a code-ready head, a round launched or closed, a verdict, a merge, a stuck agent and the action taken, a blocker added or cleared, or a decision only the operator can make. Name every such change and nothing else. Do not repeat a table, the merged list, or an unchanged blocker. If the audit found none, end the turn with no reply text. Either way, log this tick's row in your decision trail. The row names the items reported, or none."
- [ ] On the operator's hold or stand-down, send every owner a zero-writes order at once.

### Spawn owners

- [ ] Spawn one owner per PR with the full lifecycle `autopilot-stack.md` names.
- [ ] Follow this dependency graph. Start dependent work only after its parent merges.
  - [ ] BS5-01, BS5-02 and BS5-03 are independent and first. All branch from `main`.
  - [ ] BS5-04 after BS5-03. BS5-05 after BS5-02 and BS5-04. BS5-06 after BS5-05.
  - [ ] BS5-07 to BS5-15 in order, each after the one before, because shared includes move with the first family that renders them.
  - [ ] BS5-16 after BS5-15 and the flip conditions. BS5-17 about two weeks after BS5-16. BS5-18 after BS5-17.
- [ ] Hold the file boundaries. Family PRs touch only their templates, `core/templates_bs5/`, `core/static/js/bs5/`, their `_<family>.scss` partial, the built CSS, `core/harness/` and their tests. Bootstrap 3 files change only in BS5-01, BS5-17 and the preview footer link in BS5-09.
- [ ] Hold the review gate. BS5-05 to BS5-16 change an interaction. They wait for the operator's review in chat with screenshots and a video before merge.

### PR mechanics, for every PR

- [ ] There is no forge step. Each PR is a local branch `bs5/<pr-id>-<slug>` in its own worktree, cut from local `main`. Never push to `origin` and never run `gh pr create`.
- [ ] Write the PR description to `.harness/review/<pr-id>.md` with the harness summary table and the list of differences outside May change.
- [ ] Run `python manage.py test` before handing the branch to the operator. Commit with hooks on.
- [ ] Run `/simplify` before each commit. The repo has no `/deslop` or `/no-comments`.
- [ ] Keep screenshots under the ignored `.harness/` folder, never in a commit, because they show member content.
- [ ] Rebase onto current local `main` before the code-ready report. Rebase again only at merge prep or on a conflict with `main`.

### Verdict and merge, for every PR

- [ ] At the code-ready head SHA and at each later push that changes the patch, run one gates lane, the ten live lanes from the PR's **Verify, live** block, the perf lane from its **Verify, perf** block, and two audit lanes that read the diff and the receipts and distrust the PR body.
- [ ] Clean only when every lane is `PASS`. Findings go back to the owner. A new head gets a fresh verdict unless the patch-id is unchanged.
- [ ] The operator merges a clean branch into local `main`. Nothing merges on a stale verdict.

### Boot recipe, for every live lane

Each live lane runs in its own worktree at the PR head, driven by the Playwright harness.

- [ ] `git worktree add .claude/worktrees/<pr-id>-lane-<n> <head SHA>`.
- [ ] `pip install -r requirements.txt -r requirements-dev.txt`, copy `microweb/local_settings.py`, and load `HARNESS_TOKEN` from `~/.config/microweb/harness.env` (the operator's account `duncs`, never committed).
- [ ] Replay from the recorded fixtures in `.harness/fixtures/`. Record with `--record` only when the lane says so.
- [ ] Save every screenshot to `.harness/lanes/<pr-id>/<slug>.png` and return the paths with the report.

## Delete dead files (BS5-01)

**Depends on.** None.

**Files.**

- [ ] Delete `core/static/js/eventTime.js`, `m-event.js`, `m-f-event.js`, `md5.min.js`, `mozpersona.js` and `core/static/js/locales/`.
- [ ] Delete `core/static/3rd/moment.js/2.0.0/`, `3rd/leaflet/1.0.0/`, `3rd/html5shiv/`, `3rd/respond.js/` and `3rd/isogram/`.
- [ ] Delete `core/static/themes/1/css/base.css` and `core/static/img/quote-marks.png`.
- [ ] Delete `core/templates/footer.html` and `core/templates/modal_signin.html`.
- [ ] Edit `core/templates/base.html` to remove the `<!--[if lt IE 9]>` block at lines 18 to 21.

**Build.**

- [ ] Remove the files above and the IE conditional block. Nothing else changes.

**You see.**

- [ ] `git grep -nE 'eventTime|m-f-event|mozpersona|md5.min|html5shiv|respond.min|isogram|quote-marks|footer.html|modal_signin'` prints nothing outside `docs/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Run `python manage.py test --settings=microweb.travis_settings`. All existing tests pass unchanged.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Capture the 21 reference pages with `research/before-screenshots` `capture.mjs` at trunk and head. Save `BS5-01-regression.png`. Pass when every page is pixel-identical at 375 and 1280 px.
- [ ] Lane 2. Open lfgss home at 1280 px and read the browser console. Save `BS5-01-console.png`. Pass when no 404 for any static asset appears.
- [ ] Lane 3. Open a conversation page. Save `BS5-01-conversation.png`. Pass when no 404 appears and the page matches trunk.
- [ ] Lane 4. Open an event page with its map. Save `BS5-01-event.png`. Pass when Leaflet 0.7.7 still loads and draws the map.
- [ ] Lane 5. Open the event form as the operator. Save `BS5-01-event-form.png`. Pass when the datepicker and timezone list still work.
- [ ] Lane 6. Open the sign-in modal from Post a reply as a guest. Save `BS5-01-modal.png`. Pass when the inline modal in `base.html` opens.
- [ ] Lane 7. Open a profile page. Save `BS5-01-profile.png`. Pass when the page matches trunk.
- [ ] Lane 8. Open search with `defaults=true`. Save `BS5-01-search.png`. Pass when results render.
- [ ] Lane 9. Run `python manage.py collectstatic --noinput --dry-run`. Save `BS5-01-collectstatic.png` of the output. Pass when it completes without missing-file errors.
- [ ] Lane 10. Load Espruino home at 1280 px. Save `BS5-01-espruino.png`. Pass when the page matches trunk.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Total static bytes on disk under `core/static/` and gzip transfer bytes for lfgss home.
- [ ] Probe. `du -sb core/static` and the transfer size of lfgss home in Chromium DevTools, at trunk then head, twice interleaved.
- [ ] Baseline. Record the trunk byte counts first.
- [ ] Rule. Head bytes on disk must be lower than trunk. Home transfer bytes must not grow by more than 0 bytes.

**Review gate.** None. BS5-01 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Build the screenshot and interaction harness (BS5-02)

**Depends on.** None.

**Files.**

- [ ] Create `requirements-dev.txt` with Playwright for Python and `freezegun`.
- [ ] Create `core/apps.py` with `CoreConfig.ready()` that installs the recorder only when `settings.VISUAL_HARNESS` is set, and point `INSTALLED_APPS` at it.
- [ ] Create `microweb/visual_settings.py` (imports settings, sets `VISUAL_HARNESS`, swaps memcached for `LocMemCache`).
- [ ] Create `core/harness/recorder.py` (the `HTTPAdapter.send` record and replay wrapper) and `core/harness/manifest.py` (reference pages per family).
- [ ] Create `core/management/commands/shoot.py`.
- [ ] Create `core/harness/browser_tests.py` with the `browser` tag base class on `StaticLiveServerTestCase`.
- [ ] Edit `.gitignore` to ignore `.harness/` (fixtures, HARs, contact sheets).

**Build.**

- [ ] Recorder keyed by method, URL, sorted query and token presence, per [Screenshot and interaction harness design](issues/15-harness-design.md).
- [ ] `shoot` routes each Site host to the live server with the Host header preserved, records browser-side calls with Playwright HAR, freezes time with `freezegun` and `page.clock`, and writes a contact sheet with the summary table.
- [ ] Add a `--perf` flag that reports gzip CSS and JS bytes per page and server render time over 20 replayed requests, and an `--html-only` flag that writes each page's rendered HTML for byte comparison.
- [ ] Seed `manifest.py` with the 21 before pages plus signed-in pages for the harness user.

**You see.**

- [ ] `python manage.py shoot --family all --record` then `python manage.py shoot --family all` writes `.harness/<run>/index.html` with 21 pages at four widths and a summary table.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/harness/tests.py` covers the recorder key, record then replay round trip, and a missing fixture raising a clear error. Run `python manage.py test core.harness`.
- [ ] `python manage.py test` without `--tag browser` still skips browser tests.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Trunk has no harness, so record that and gate the end state. Run `python manage.py shoot --family all` twice from one recording. Save `BS5-02-regression.png`. Pass when both runs produce pixel-identical images.
- [ ] Lane 2. Run with the network disabled after recording. Save `BS5-02-offline.png`. Pass when every page still renders from fixtures.
- [ ] Lane 3. Open the contact sheet. Save `BS5-02-sheet.png`. Pass when before and after sit side by side per page, width and Color mode.
- [ ] Lane 4. Read the summary table. Save `BS5-02-summary.png`. Pass when it shows page height at 1280 px, rows above the fold and check results.
- [ ] Lane 5. Shoot a conversation page with relative times on two different days. Save `BS5-02-clock.png`. Pass when the `<time>` text is identical.
- [ ] Lane 6. Shoot a signed-in conversation page with `HARNESS_TOKEN` set. Save `BS5-02-member.png`. Pass when the reply box renders.
- [ ] Lane 7. Shoot the test huddle. Save `BS5-02-huddle.png`. Pass when it renders and no fixture file is tracked by git.
- [ ] Lane 8. Run `python manage.py test --tag browser` with one sample check (the page jump input). Save `BS5-02-check.png`. Pass when it passes.
- [ ] Lane 9. Shoot Espruino and CS Grupetto home. Save `BS5-02-branding.png`. Pass when background images load through the `microco.sm` to `microcosm.app` rewrite.
- [ ] Lane 10. Run `git status --ignored`. Save `BS5-02-ignored.png`. Pass when `.harness/` is ignored and nothing under it is staged.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Wall time of a full `shoot --family all` replay run.
- [ ] Probe. Time the run at head three times. Trunk has no harness, so also record time per page.
- [ ] Baseline. Record the first run as the baseline.
- [ ] Rule. A full replay run finishes under 10 minutes on the operator's machine, and under 15 seconds per page.

**Review gate.** None. BS5-02 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Add the Sass, font and icon toolchain (BS5-03)

**Depends on.** None.

**Files.**

- [ ] Create `core/static/scss/vendor/bootstrap/` with Bootstrap 5.3.8 `scss/`.
- [ ] Create `core/static/themes/1/scss/tokens.scss` (about 16 variables) and `core/static/themes/1/scss/site.scss`.
- [ ] Create `bin/build-css` that downloads a pinned dart-sass 1.x into `.cache/` and compiles to `core/static/themes/1/css/bs5.min.css` with a source hash header.
- [ ] Create `core/static/3rd/bootstrap/5.3.8/bootstrap.bundle.min.js`.
- [ ] Create `core/static/fonts/` with Source Sans 3 and Merriweather `.woff2`.
- [ ] Create `core/icons/bootstrap-icons/` with about 26 SVGs and a `VERSION` note of 1.13.1, and `core/templatetags/icon.py`.

**Build.**

- [ ] `bin/build-css` silences the `import`, `global-builtin`, `color-functions` and `if-function` deprecations for vendored sources, per [Sass build or compiled CSS](issues/02-sass-or-compiled.md).
- [ ] `{% icon %}` inlines cached SVGs, decorative by default, `label=` gives `role="img"`, per [How templates reference icons](issues/13-icons.md).

**You see.**

- [ ] `bin/build-css` prints the output path and the hash, and `git diff --stat` after a second run shows no change.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_css_fresh.py` fails when the hash of `core/static/themes/1/scss/` differs from the CSS header. Run `python manage.py test core.tests.test_css_fresh`.
- [ ] `core/tests/test_icon_tag.py` covers decorative output, labelled output, the class argument and an unknown name raising. Run `python manage.py test core.tests.test_icon_tag`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Shoot `--family all` with `?bs=3` at trunk and head. Save `BS5-03-regression.png`. Pass when every image is identical, because nothing renders the new files yet.
- [ ] Lane 2. Run `bin/build-css` on a clean clone. Save `BS5-03-build.png`. Pass when it downloads dart-sass once and writes the CSS.
- [ ] Lane 3. Edit one token and run the unit tests without rebuilding. Save `BS5-03-stale.png`. Pass when the freshness test fails with a message naming `bin/build-css`.
- [ ] Lane 4. Render a scratch template with `{% icon "lock" label="Closed" %}`. Save `BS5-03-icon.png`. Pass when the SVG has `role="img"` and `aria-label`.
- [ ] Lane 5. Render `{% icon "search" %}`. Save `BS5-03-icon-decorative.png`. Pass when it has `aria-hidden="true"` and `focusable="false"`.
- [ ] Lane 6. Serve `bs5.min.css` with `DEBUG=True`. Save `BS5-03-static.png`. Pass when whitenoise serves it with a hashed name after `collectstatic`.
- [ ] Lane 7. Load each `.woff2` in a scratch page. Save `BS5-03-fonts.png`. Pass when Source Sans 3 and Merriweather render with no Google Fonts request.
- [ ] Lane 8. Build the Docker image. Save `BS5-03-docker.png`. Pass when the Dockerfile is unchanged and the image builds.
- [ ] Lane 9. Load `bootstrap.bundle.min.js` in a scratch page. Save `BS5-03-bundle.png`. Pass when `window.bootstrap.Modal` exists.
- [ ] Lane 10. Check the Sass output for dark mode tokens. Save `BS5-03-dark-tokens.png`. Pass when `[data-bs-theme=dark]` rules are present.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Gzip size of `bs5.min.css` and `bin/build-css` wall time.
- [ ] Probe. Measure at head three times. Trunk has no Bootstrap 5 CSS, so compare against trunk `theme.css` gzip size as the budget reference.
- [ ] Baseline. Record trunk `theme.css` gzip size first (about 30 KB).
- [ ] Rule. `bs5.min.css` gzip stays under 36 KB and a build finishes under 5 seconds.

**Review gate.** None. BS5-03 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Add the Bootstrap 5 template engine, render shim and preview cookie (BS5-04)

**Depends on.** BS5-03.

**Files.**

- [ ] Edit `microweb/settings.py` to add the `bs5` engine with `core/templates_bs5/` first and app dirs after.
- [ ] Create `core/framework.py` with `render()` and `wants_bs5()`.
- [ ] Edit the 15 view modules and `core/views.py` error views to import `render` from `core/framework.py`.
- [ ] Create `core/templates_bs5/.keep`.

**Build.**

- [ ] A page renders on Bootstrap 5 only when `?bs=5` or the `bs` cookie asks and its page template exists in `core/templates_bs5/`, per [How Bootstrap 3 and 5 coexist while PRs ship one at a time](issues/01-coexistence.md). `?bs=` sets the cookie.

**You see.**

- [ ] With no files in the bs5 tree, `?bs=5` on any page returns the same HTML as trunk.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_framework.py` covers engine choice by cookie, query and template existence, include fallback to the Bootstrap 3 file, and cookie setting. Run `python manage.py test core.tests.test_framework`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Shoot `--family all` at trunk and at head with `?bs=5`. Save `BS5-04-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Request lfgss home with `?bs=5`. Save `BS5-04-cookie.png`. Pass when the response sets `bs=5` with `SameSite=Lax`.
- [ ] Lane 3. Request with `?bs=3` after `bs=5`. Save `BS5-04-optout.png`. Pass when the cookie becomes `bs=3`.
- [ ] Lane 4. Place a scratch page template in the bs5 tree in a local branch only. Save `BS5-04-scratch.png`. Pass when that page renders from the bs5 engine and other pages stay Bootstrap 3.
- [ ] Lane 5. Trigger a 404 with `?bs=5`. Save `BS5-04-404.png`. Pass when the Bootstrap 3 error page renders.
- [ ] Lane 6. Trigger a 403 on a private huddle as a guest. Save `BS5-04-403.png`. Pass when the page renders.
- [ ] Lane 7. Hit `/health/ready`. Save `BS5-04-health.png`. Pass when it returns 200 without touching the API.
- [ ] Lane 8. Check the `Cache-Control` header on a view. Save `BS5-04-cache.png`. Pass when it is still `max-age=0, must-revalidate`.
- [ ] Lane 9. Run the full unit suite. Save `BS5-04-tests.png`. Pass when all tests pass.
- [ ] Lane 10. Load Islington CC home with `?bs=5`. Save `BS5-04-islington.png`. Pass when it matches trunk.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Server render time for lfgss home and a conversation page.
- [ ] Probe. `shoot --perf` on both pages, trunk then head, three interleaved rounds.
- [ ] Baseline. Record trunk median render time first.
- [ ] Rule. Head median render time must be within 5 percent or 1 ms of trunk, whichever is larger.

**Review gate.** None. BS5-04 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Build the Bootstrap 5 base layout (BS5-05)

**Depends on.** BS5-02 and BS5-04.

**Files.**

- [ ] Create `core/templates_bs5/base.html` (header, navbar, footer, offcanvas drawers, sign-in modal).
- [ ] Create `core/static/themes/1/scss/_base.scss` (the `mw-` button variant, `.mw-panel`, logo height, prose basics).
- [ ] Create `core/static/js/bs5/base.js` and `core/static/js/bs5/metabar.js` as ES modules.
- [ ] Edit `core/harness/manifest.py` and add base checks to `core/harness/browser_tests.py`.

**Build.**

- [ ] Header, navbar and footer follow the Must hold list in [How close is close enough](issues/05-close-enough.md).
- [ ] `authSignin()` hides `#modal-signin` and opens Lock on `hidden.bs.modal`, per [Whether Bootstrap 5's modal focus trap blocks Auth0 Lock](issues/10-modal-vs-auth0-lock.md). Lock is pinned to `color-scheme: light`.
- [ ] Ported `base.js` renders relative times with `Intl.RelativeTimeFormat` and uses `new bootstrap.Tooltip`, per [How app scripts run on Bootstrap 5 pages](issues/11-scripts-on-bs5-pages.md). jQuery still loads as the safety net.

**You see.**

- [ ] A scratch page template in a local branch renders inside the new base with the lfgss header, navbar and footer.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_base.py` renders the base with a guest and a member context and asserts no `data-toggle=`, no `sprite-` and no `$(` in the output. Run `python manage.py test core.tests.test_bs5_base`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Trunk has no Bootstrap 5 base, so record that and gate the end state. Shoot `--family all` with `?bs=3` at trunk and head. Save `BS5-05-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Shoot the base with a scratch page at 375 px. Save `BS5-05-375.png`. Pass when the two drawer buttons sit either side of the logo.
- [ ] Lane 3. Open the menu drawer and the metabar drawer at 375 px. Save `BS5-05-drawers.png`. Pass when both open, trap focus, and close on Escape.
- [ ] Lane 4. Shoot the base at 1280 px. Save `BS5-05-1280.png`. Pass when the account box is right, search is right of the nav row, and the 9 to 3 columns hold.
- [ ] Lane 5. Click Sign in from the modal as a guest. Save `BS5-05-lock.png`. Pass when the modal closes and the Lock email field accepts typing.
- [ ] Lane 6. Click Sign In in the navbar with no modal open. Save `BS5-05-lock-navbar.png`. Pass when Lock opens directly.
- [ ] Lane 7. Hover a tooltip element. Save `BS5-05-tooltip.png`. Pass when the Bootstrap 5 tooltip shows and the console has no errors.
- [ ] Lane 8. Read `<time>` elements with a frozen clock. Save `BS5-05-time.png`. Pass when the text matches `Intl.RelativeTimeFormat` output in English.
- [ ] Lane 9. Shoot the base on Espruino at 1280 px. Save `BS5-05-espruino.png`. Pass when the background image, logo height and link colour hold.
- [ ] Lane 10. Shoot the base with keyboard focus on each nav link. Save `BS5-05-focus.png`. Pass when focus rings are visible on every control.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Gzip CSS and JS bytes and render time for the scratch page on the new base against lfgss home on trunk.
- [ ] Probe. `shoot --perf` at trunk (home, Bootstrap 3) and head (scratch page, Bootstrap 5), three interleaved rounds.
- [ ] Baseline. Record trunk bytes and render time first.
- [ ] Rule. The scenarios differ, so use absolute budgets. Gzip CSS plus JS under 115 percent of trunk while jQuery remains, and render time within 5 percent or 1 ms of trunk, whichever is larger.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-05-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-05-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Add the Color mode toggle (BS5-06)

**Depends on.** BS5-05.

**Files.**

- [ ] Edit `core/middleware/context.py` to read the `color_mode` cookie.
- [ ] Edit `core/templates_bs5/base.html` for `data-bs-theme`, the Auto head script and the navbar toggle.
- [ ] Create `core/colors.py` with the AA link colour adjustment and `core/templatetags/color.py`.
- [ ] Edit `core/static/themes/1/scss/tokens.scss` for dark tokens if needed, then run `bin/build-css`.

**Build.**

- [ ] Light, Dark and Auto per [How the Color mode is chosen and applied, and how Site branding adapts to dark](issues/03-color-mode-mechanism.md). Auto uses Bootstrap's documented head script. The Site surround never changes with the mode.

**You see.**

- [ ] Choosing Dark in the navbar toggle reloads nothing and the next page load starts dark with no flash.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_colors.py` covers hex parsing, the AA adjustment for `#21201b`, `#51a9ff` and `#1e72c4` against the dark body colour, and hover shades. Run `python manage.py test core.tests.test_colors`.
- [ ] `core/middleware/tests.py` gains cases for each cookie value and a missing cookie.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Trunk has no Color mode, so record that and gate the end state. Shoot `--family all` with `?bs=3` at trunk and head. Save `BS5-06-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Choose Dark on lfgss. Save `BS5-06-dark.png`. Pass when `data-bs-theme=dark` is set and the surround stays `#424143`.
- [ ] Lane 3. Reload after choosing Dark with a network throttle. Save `BS5-06-noflash.png`. Pass when the first painted frame is dark.
- [ ] Lane 4. Choose Auto with the system set to dark. Save `BS5-06-auto.png`. Pass when the page is dark and follows a live system change.
- [ ] Lane 5. Load wwcc with Dark. Save `BS5-06-wwcc.png`. Pass when its `#21201b` links reach 4.5 to 1.
- [ ] Lane 6. Load lesperitdelbikepacking in Light. Save `BS5-06-light-exact.png`. Pass when the link colour is exactly the Site colour.
- [ ] Lane 7. Operate the toggle by keyboard only. Save `BS5-06-keyboard.png`. Pass when every option is reachable and announced.
- [ ] Lane 8. Load outliers in Dark. Save `BS5-06-outliers.png`. Pass when the dark surround and logo hold.
- [ ] Lane 9. Load with the cookie removed. Save `BS5-06-default.png`. Pass when Auto applies.
- [ ] Lane 10. Open the sign-in modal in Dark and start Lock. Save `BS5-06-lock.png`. Pass when Lock renders light.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time to first paint and render time on lfgss home with Auto.
- [ ] Probe. `shoot --perf` at trunk and head, three interleaved rounds.
- [ ] Baseline. Record trunk first paint first.
- [ ] Rule. First paint must not regress by more than 20 ms, and render time by no more than 5 percent or 1 ms, whichever is larger.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-06-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-06-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the forum lists family (BS5-07)

**Depends on.** BS5-06.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `microcosms.html`, `microcosm.html`, `block_microcosm.html`, `block_conversation.html`, `block_event.html`, `pagination.html`, `breadcrumbs.html` and `forms/mark-read.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/themes/1/scss/_lists.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the lists pages and checks.

**Build.**

- [ ] Rebuild the lists templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, lfgss home and a microcosm listing render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_lists.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_lists`.
- [ ] Run `python manage.py test --tag browser` for the lists interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family lists --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 lists pages, so also gate that every lists page renders 200 at head with `?bs=5`. Save `BS5-07-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot lfgss home and a microcosm listing at 375 px, light. Save `BS5-07-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-07-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-07-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-07-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-07-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_lists.scss` prints nothing.
- [ ] Lane 7. Type 3 in the page jump input on a microcosm listing and press Enter. Save `BS5-07-check-a.png`. Pass when the page loads at offset 50.
- [ ] Lane 8. Click Mark all as read as the harness user. Save `BS5-07-check-b.png`. Pass when the NEW badges disappear after reload.
- [ ] Lane 9. Shoot lfgss home as the harness user. Save `BS5-07-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Espruino at 1280 px, light and dark. Save `BS5-07-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Rows above the fold on home at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family lists --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-07-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-07-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the conversations and comments family (BS5-08)

**Depends on.** BS5-07.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `conversation.html`, `comment.html`, `block_comments.html`, `block_comment_single.html`, `forms/block_comment_box.html`, `forms/create_comment.html`, `forms/conversation.html` and `modal_formatting_help.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/simpleEditor.js`, `comments.js`, `attachments.js` and `mentions.js`.
- [ ] Create `core/static/themes/1/scss/_conversations.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the conversations pages and checks.

**Build.**

- [ ] Rebuild the conversations templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, `/conversations/141600/` and `/conversations/357218/?offset=250` render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_conversations.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_conversations`.
- [ ] Run `python manage.py test --tag browser` for the conversations interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family conversations --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 conversations pages, so also gate that every conversations page renders 200 at head with `?bs=5`. Save `BS5-08-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot `/conversations/141600/` and `/conversations/357218/?offset=250` at 375 px, light. Save `BS5-08-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-08-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-08-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-08-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-08-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_conversations.scss` prints nothing.
- [ ] Lane 7. As the harness user, select comment text and click Post a reply. Save `BS5-08-check-a.png`. Pass when the reply box opens with the selection quoted.
- [ ] Lane 8. Type `@` and two letters in the reply box. Save `BS5-08-check-b.png`. Pass when `mentions.js` lists up to five profiles, arrow keys move the active option, and Enter inserts the name.
- [ ] Lane 9. Post, edit and delete a comment in a test conversation as the harness user. Save `BS5-08-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Islington CC at 1280 px, light and dark. Save `BS5-08-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Page height of both conversation pages at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family conversations --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-08-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-08-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the profiles family (BS5-09)

**Depends on.** BS5-08.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `profile.html` (drop the missing `microweb_templates/list_items.html` includes), `profiles.html`, `block_profile.html`, `forms/profile.html`, `forms/update_settings.html` and `ignored.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/filters.js` and `profilePicture.js`.
- [ ] Edit the Bootstrap 3 and 5 footers to add the member preview links.
- [ ] Create `core/static/themes/1/scss/_profiles.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the profiles pages and checks.

**Build.**

- [ ] Rebuild the profiles templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, a profile page and the people list render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_profiles.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_profiles`.
- [ ] Run `python manage.py test --tag browser` for the profiles interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family profiles --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 profiles pages, so also gate that every profiles page renders 200 at head with `?bs=5`. Save `BS5-09-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot a profile page and the people list at 375 px, light. Save `BS5-09-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-09-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-09-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-09-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-09-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_profiles.scss` prints nothing.
- [ ] Lane 7. Filter the people list by online now. Save `BS5-09-check-a.png`. Pass when the list updates and the URL carries the filter.
- [ ] Lane 8. Upload a new avatar on the harness user's edit page. Save `BS5-09-check-b.png`. Pass when the preview shows the image before save.
- [ ] Lane 9. Change notification settings as the harness user. Save `BS5-09-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on CS Grupetto at 1280 px, light and dark. Save `BS5-09-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Page height of a profile page at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family profiles --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-09-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-09-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the activity lists family (BS5-10)

**Depends on.** BS5-09.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `updates.html`, `watchers.html`, `today.html`, `trending.html`, `search.html` and `block_list_comments.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/themes/1/scss/_activity.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the activity pages and checks.

**Build.**

- [ ] Rebuild the activity templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, Following, Today, Trending and search render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_activity.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_activity`.
- [ ] Run `python manage.py test --tag browser` for the activity interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family activity --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 activity pages, so also gate that every activity page renders 200 at head with `?bs=5`. Save `BS5-10-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot Following, Today, Trending and search at 375 px, light. Save `BS5-10-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-10-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-10-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-10-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-10-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_activity.scss` prints nothing.
- [ ] Lane 7. Search `bike` from the navbar. Save `BS5-10-check-a.png`. Pass when results render with `defaults=true` carried.
- [ ] Lane 8. Stop following an item on the watchers page as the harness user. Save `BS5-10-check-b.png`. Pass when it disappears after reload.
- [ ] Lane 9. Shoot Following as the harness user. Save `BS5-10-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Islington CC at 1280 px, light and dark. Save `BS5-10-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Rows above the fold on Following at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family activity --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-10-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-10-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the events family (BS5-11)

**Depends on.** BS5-10.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `event.html`, `event_header_large.html`, `event_header_small.html`, `block_event.html` updates and `modal_event_attendees.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/eventMap.js`.
- [ ] Create `core/static/themes/1/scss/_events.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the events pages and checks.

**Build.**

- [ ] Rebuild the events templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, `/events/4488/` and an event list render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_events.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_events`.
- [ ] Run `python manage.py test --tag browser` for the events interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family events --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 events pages, so also gate that every events page renders 200 at head with `?bs=5`. Save `BS5-11-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot `/events/4488/` and an event list at 375 px, light. Save `BS5-11-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-11-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-11-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-11-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-11-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_events.scss` prints nothing.
- [ ] Lane 7. Open the attendees modal. Save `BS5-11-check-a.png`. Pass when it opens, traps focus and closes on Escape.
- [ ] Lane 8. Pan the event map. Save `BS5-11-check-b.png`. Pass when Leaflet draws tiles and stays in `color-scheme: light` in Dark.
- [ ] Lane 9. RSVP to a test event as the harness user. Save `BS5-11-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Espruino at 1280 px, light and dark. Save `BS5-11-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Page height of an event page at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family events --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-11-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-11-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the event form (BS5-12)

**Depends on.** BS5-11.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `forms/event.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/eventForm.js` and `eventFormClasses.js`.
- [ ] Create `core/static/themes/1/scss/_event_form.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the event_form pages and checks.

**Build.**

- [ ] Rebuild the event_form templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, the create and edit event forms render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_event_form.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_event_form`.
- [ ] Run `python manage.py test --tag browser` for the event_form interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family event_form --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 event_form pages, so also gate that every event_form page renders 200 at head with `?bs=5`. Save `BS5-12-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot the create and edit event forms at 375 px, light. Save `BS5-12-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-12-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-12-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-12-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-12-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_event_form.scss` prints nothing.
- [ ] Lane 7. Pick a date and time with the native inputs and submit. Save `BS5-12-check-a.png`. Pass when the API receives an ISO 8601 value that `core/forms/forms.py` parses.
- [ ] Lane 8. Open the timezone list. Save `BS5-12-check-b.png`. Pass when it comes from `Intl.supportedValuesOf` and defaults to the browser time zone.
- [ ] Lane 9. Edit an existing test event as the harness user. Save `BS5-12-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Islington CC at 1280 px, light and dark. Save `BS5-12-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time to interactive on the event form, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family event_form --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-12-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-12-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the huddles family (BS5-13)

**Depends on.** BS5-12.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `huddles.html`, `huddle.html`, `block_huddle.html`, `forms/huddle.html`, `modal_huddle_invite.html` and `modal_huddle_leave.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/peopleWidget.js`.
- [ ] Create `core/static/themes/1/scss/_huddles.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the huddles pages and checks.

**Build.**

- [ ] Rebuild the huddles templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, the huddle list and the test huddle render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_huddles.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_huddles`.
- [ ] Run `python manage.py test --tag browser` for the huddles interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family huddles --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 huddles pages, so also gate that every huddles page renders 200 at head with `?bs=5`. Save `BS5-13-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot the huddle list and the test huddle at 375 px, light. Save `BS5-13-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-13-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-13-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-13-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-13-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_huddles.scss` prints nothing.
- [ ] Lane 7. Type a name into the people widget in the self-huddle's invite modal, without sending. Save `BS5-13-check-a.png`. Pass when the widget suggests matching profiles.
- [ ] Lane 8. Leave the test huddle from the modal. Save `BS5-13-check-b.png`. Pass when the huddle leaves the list.
- [ ] Lane 9. Reply in the self-huddle as the harness user. Save `BS5-13-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Islington CC at 1280 px, light and dark. Save `BS5-13-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Page height of the test huddle at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family huddles --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-13-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-13-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the forum admin family (BS5-14)

**Depends on.** BS5-13.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `forms/microcosm.html`, `memberships.html`, `forms/memberships.html`, `forms/moderation_item.html`, `forms/content-moderation.html`, `forms/metabar-moderation.html` and `forms/subscribe.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/js/bs5/membership_form.js`.
- [ ] Create `core/static/themes/1/scss/_admin.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the admin pages and checks.

**Build.**

- [ ] Rebuild the admin templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, the membership groups page and the microcosm form render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_admin.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_admin`.
- [ ] Run `python manage.py test --tag browser` for the admin interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family admin --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 admin pages, so also gate that every admin page renders 200 at head with `?bs=5`. Save `BS5-14-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot the membership groups page and the microcosm form at 375 px, light. Save `BS5-14-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-14-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-14-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-14-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-14-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_admin.scss` prints nothing.
- [ ] Lane 7. Add a criterion to a test membership group as the operator. Save `BS5-14-check-a.png`. Pass when `membership_form.js` saves it and it reloads intact.
- [ ] Lane 8. Follow and unfollow a conversation. Save `BS5-14-check-b.png`. Pass when the switch toggles and the email checkbox follows.
- [ ] Lane 9. Shoot moderation controls as the operator on a test microcosm. Save `BS5-14-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on Islington CC at 1280 px, light and dark. Save `BS5-14-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Time to interactive on the memberships form, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family admin --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-14-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-14-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Migrate the legal and error pages (BS5-15)

**Depends on.** BS5-14.

**Files.**

- [ ] Create `core/templates_bs5/` copies of `legal.html`, `legals.html`, `403.html`, `404.html` and `500.html` in a first commit, unchanged, then edit them in a second commit.
- [ ] Create `core/static/themes/1/scss/_legal.scss` and run `bin/build-css`.
- [ ] Edit `core/harness/manifest.py` and `core/harness/browser_tests.py` for the legal pages and checks.

**Build.**

- [ ] Rebuild the legal templates clean room with Bootstrap 5 components and utilities, per [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md). Swap sprites for `{% icon %}` using the mapping table.
- [ ] Port the family's scripts to ES modules in `core/static/js/bs5/`, with no new jQuery.

**You see.**

- [ ] With `?bs=5`, `/about/terms/`, `/about/` and the three error pages render on the Bootstrap 5 base, and the debug trace shows every family template served from `core/templates_bs5/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_bs5_legal.py` renders each family template and asserts no `data-toggle=`, no `sprite-`, no `$(` and no colour literal in the partial. Run `python manage.py test core.tests.test_bs5_legal`.
- [ ] Run `python manage.py test --tag browser` for the legal interaction checks.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Run `python manage.py shoot --family legal --html-only` at trunk and at head with `?bs=3` on the same replay fixtures. Trunk has no Bootstrap 5 legal pages, so also gate that every legal page renders 200 at head with `?bs=5`. Save `BS5-15-regression.png`. Pass when the Bootstrap 3 HTML is byte-identical between trunk and head and every `?bs=5` page returns 200.
- [ ] Lane 2. Shoot `/about/terms/`, `/about/` and the three error pages at 375 px, light. Save `BS5-15-375.png`. Pass when every difference from `?bs=3` is on the May change list in [How close is close enough](issues/05-close-enough.md) or is listed in the PR body for the operator.
- [ ] Lane 3. Shoot the same pages at 768 px, light. Save `BS5-15-768.png`. Pass when the column tiers chosen in the PR body hold and nothing overflows horizontally.
- [ ] Lane 4. Shoot the same pages at 1280 px, light, and read the contact sheet summary. Save `BS5-15-1280.png`. Pass when page height grows by 10 percent or less against `?bs=3` and list pages show at least as many rows above the fold.
- [ ] Lane 5. Shoot the same pages at 1440 px, light. Save `BS5-15-1440.png`. Pass when the layout uses the 1320 px container without stretched rows or orphaned whitespace the PR body does not explain.
- [ ] Lane 6. Shoot the same pages at 1280 px with `color_mode=dark`. Save `BS5-15-dark.png`. Pass when all text is readable, the Site surround matches light mode, and `grep -E '#[0-9a-fA-F]{3,8}|rgba?\(' core/static/scss/_legal.scss` prints nothing.
- [ ] Lane 7. Open `/about/terms/`. Save `BS5-15-check-a.png`. Pass when tables and `ol[type=a]` and `ol[type=i]` lists render with Bootstrap 5 styling.
- [ ] Lane 8. Request a missing URL. Save `BS5-15-check-b.png`. Pass when the 404 page renders on the Bootstrap 5 base.
- [ ] Lane 9. Request a huddle id the harness user cannot see. Save `BS5-15-signed-in.png`. Pass when the signed-in controls render, work, and match the tolerance checklist.
- [ ] Lane 10. Shoot the family's main page on CS Grupetto at 1280 px, light and dark. Save `BS5-15-branding.png`. Pass when the Site background, logo and link colour hold, and the dark-mode link colour reaches 4.5 to 1 against the body background.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Page height of the terms page at 1280 px, gzip CSS and JS bytes per page, and server render time.
- [ ] Probe. `python manage.py shoot --family legal --perf` with `?bs=3` and `?bs=5` on the same checkout at head, three interleaved rounds, plus trunk with `?bs=3`.
- [ ] Baseline. Record the trunk `?bs=3` values first.
- [ ] Rule. Render time within 5 percent or 1 ms of trunk, whichever is larger. Gzip CSS plus JS under 115 percent of trunk while jQuery remains. Page height rule from the tolerance checklist.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-15-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-15-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Flip every visitor to Bootstrap 5 (BS5-16)

**Depends on.** BS5-15, plus the flip conditions in [Order of the PRs, from scaffolding to flip](issues/12-family-order.md).

**Files.**

- [ ] Edit `core/framework.py` so Bootstrap 5 is the default and `?bs=3` still opts out.
- [ ] Edit both footers to drop the preview links.

**Build.**

- [ ] Default to Bootstrap 5 for every page. Keep `?bs=3` working for about two weeks.

**You see.**

- [ ] A fresh browser with no cookie gets Bootstrap 5 on every page.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] `core/tests/test_framework.py` gains the default case and the `?bs=3` escape case. Run `python manage.py test core.tests.test_framework`.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Shoot `--family all` at trunk with `?bs=5` and at head with no cookie. Save `BS5-16-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Load every manifest page with no cookie. Save `BS5-16-all.png`. Pass when the debug trace shows no Bootstrap 3 template.
- [ ] Lane 3. Load with `?bs=3`. Save `BS5-16-escape.png`. Pass when the Bootstrap 3 page renders.
- [ ] Lane 4. Run all interaction checks in Chromium. Save `BS5-16-chromium.png`. Pass when all pass.
- [ ] Lane 5. Run all interaction checks in Firefox. Save `BS5-16-firefox.png`. Pass when all pass.
- [ ] Lane 6. Run all interaction checks in WebKit. Save `BS5-16-webkit.png`. Pass when all pass.
- [ ] Lane 7. Check the mentions listbox with VoiceOver and NVDA. Save `BS5-16-a11y.png`. Pass when options are announced as the active option moves.
- [ ] Lane 8. Shoot every Site in the manifest in Dark. Save `BS5-16-dark.png`. Pass when every page is readable.
- [ ] Lane 9. Sign in through Lock from a cold browser. Save `BS5-16-signin.png`. Pass when the session returns to the page.
- [ ] Lane 10. Load `/health/ready`. Save `BS5-16-health.png`. Pass when it returns 200.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Server render time and gzip CSS plus JS bytes for the whole manifest.
- [ ] Probe. `shoot --family all --perf` at trunk (`?bs=5`) and head (no cookie), three interleaved rounds.
- [ ] Baseline. Record trunk values first.
- [ ] Rule. Head must be within 2 percent of trunk on both, because the pages are the same.

**Review gate.** The operator reviews before merge.

- [ ] Copy the lane 2 to 6 screenshots into `.harness/review/BS5-16-review-<slug>.png`.
- [ ] Record a 30 to 60 second Playwright video of the change. Save it as `.harness/review/BS5-16-review.webm`.
- [ ] Show the screenshots and the video to the operator in chat, with the list of differences outside May change. Stop at merge-ready. Wait for the operator's click.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Delete Bootstrap 3 and the old scripts (BS5-17)

**Depends on.** BS5-16, about two weeks after it lands.

**Files.**

- [ ] Delete every Bootstrap 3 template in `core/templates/` that has a bs5 copy.
- [ ] Move `core/static/js/Markdown.Converter.js` to `core/static/3rd/`, and point `core/static/js/bs5/simpleEditor.js` at it, before deleting the old scripts. Preview needs it (BS5-08).
- [ ] Delete `core/static/themes/1/css/theme.css`, `core/static/js/bootstrap.min.js`, `img/icons.png`, `img/icons@2x.png` and the unported `core/static/js/*.js`.
- [ ] Delete `core/static/3rd/jquery/`, `3rd/moment.js/`, `3rd/moment-timezone/`, `3rd/jsTimezoneDetect/`, `3rd/timezones/` and `core/static/js/jquery.textcomplete.min.js`.
- [ ] Edit `core/templates_bs5/base.html` to stop loading jQuery.
- [ ] Edit `core/framework.py` to remove the `?bs=3` escape.

**Build.**

- [ ] Remove everything the flip made unreachable. `preloader.gif` goes if nothing references it.

**You see.**

- [ ] `git grep -nE 'jquery|moment|sprite-|theme.css|data-toggle'` prints nothing outside `docs/`.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Run `python manage.py test` and `python manage.py test --tag browser`. All pass.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Shoot `--family all` at trunk and head. Save `BS5-17-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Open the console on every manifest page. Save `BS5-17-console.png`. Pass when no page references `$` or `jQuery`.
- [ ] Lane 3. Post a reply with a mention. Save `BS5-17-mention.png`. Pass when it works without jQuery.
- [ ] Lane 4. Submit the event form. Save `BS5-17-event.png`. Pass when the ISO date is accepted.
- [ ] Lane 5. Edit a membership group. Save `BS5-17-membership.png`. Pass when it saves.
- [ ] Lane 6. Invite to a huddle. Save `BS5-17-huddle.png`. Pass when the people widget works.
- [ ] Lane 7. Run `collectstatic`. Save `BS5-17-collectstatic.png`. Pass when no missing file is reported.
- [ ] Lane 8. Request `?bs=3`. Save `BS5-17-nobs3.png`. Pass when Bootstrap 5 renders anyway.
- [ ] Lane 9. Check Network for 404s across the manifest. Save `BS5-17-404.png`. Pass when there are none.
- [ ] Lane 10. Build the Docker image. Save `BS5-17-docker.png`. Pass when it builds and the image is smaller than trunk.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Gzip CSS plus JS bytes per page and static bytes on disk.
- [ ] Probe. `shoot --family all --perf` and `du -sb core/static` at trunk and head, interleaved.
- [ ] Baseline. Record trunk values first.
- [ ] Rule. Head gzip CSS plus JS per page must be below the pre-migration Bootstrap 3 value recorded in BS5-01.

**Review gate.** None. BS5-17 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Rename the Bootstrap 5 tree into place and remove the switch (BS5-18)

**Depends on.** BS5-17.

**Files.**

- [ ] Rename `core/templates_bs5/` to `core/templates/` and `core/static/js/bs5/` to `core/static/js/` with `git mv` only, in a first commit.
- [ ] Edit `microweb/settings.py` to remove the `bs5` engine.
- [ ] Delete `core/framework.py` and restore `django.shortcuts.render` imports in the view modules.
- [ ] Edit `core/harness/` to drop `?bs=` handling.

**Build.**

- [ ] The first commit is pure renames. The second removes the engine, the shim and the cookie.

**You see.**

- [ ] `git show --stat HEAD~1` lists only renames.

**Verify, unit.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Run `python manage.py test` and `python manage.py test --tag browser`. All pass.

**Verify, live.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked. Ten lanes on `sonnet` at the PR head, per the boot recipe.

- [ ] Lane 1. Regression lane against trunk. Shoot `--family all` at trunk and head. Save `BS5-18-regression.png`. Pass when every image is identical.
- [ ] Lane 2. Run `git show -M --stat HEAD~1`. Save `BS5-18-renames.png`. Pass when every line is a 100 percent rename.
- [ ] Lane 3. Send a `bs=5` cookie. Save `BS5-18-cookie.png`. Pass when nothing sets or reads it.
- [ ] Lane 4. Run all interaction checks. Save `BS5-18-checks.png`. Pass when all pass.
- [ ] Lane 5. Load `/health/ready`. Save `BS5-18-health.png`. Pass when it returns 200.
- [ ] Lane 6. Trigger 403, 404 and 500. Save `BS5-18-errors.png`. Pass when each renders on the Bootstrap 5 base.
- [ ] Lane 7. Build the Docker image and run it. Save `BS5-18-docker.png`. Pass when lfgss home renders.
- [ ] Lane 8. Grep for `templates_bs5` and `js/bs5`. Save `BS5-18-grep.png`. Pass when nothing matches outside `docs/`.
- [ ] Lane 9. Load Espruino, CS Grupetto, Islington CC and outliers. Save `BS5-18-sites.png`. Pass when each matches trunk.
- [ ] Lane 10. Toggle Color mode on lfgss. Save `BS5-18-colormode.png`. Pass when it matches trunk.

**Verify, perf.** Tests alone are not sufficient verification. A PR is verified only when its unit, live, and perf boxes are all checked.

- [ ] Metric. Server render time across the manifest.
- [ ] Probe. `shoot --family all --perf` at trunk and head, three interleaved rounds.
- [ ] Baseline. Record trunk values first.
- [ ] Rule. Head within 2 percent of trunk.

**Review gate.** None. BS5-18 is not review-gated.

**Merge.**

- [ ] Clean verdict at the exact head SHA.
- [ ] The operator's review notes triaged.
- [ ] Rebased onto current local `main` after the verdict, patch-id unchanged.
- [ ] The operator squash-merges the branch into local `main`.

## Close the program

- [ ] Every box above is checked with its evidence.
- [ ] Hand the operator the post-migration follow-up to test the BS5-08 formatting toolbar properly (dropped Ctrl+U, H and R, no Shift+Enter list continuation, browser undo, toggling Quote and List), which the operator accepted at merge for testing later.
- [ ] Reply to the operator with the report `autopilot-stack.md` names, and move `.scratch/bootstrap5/` decision tickets into `docs/` or delete them.

## Appendix A. Prototype evidence

- Coexistence. Branch `prototype/bs5-coexistence` at `53776fa1`. A second template engine with name fallback. See [How Bootstrap 3 and 5 coexist while PRs ship one at a time](issues/01-coexistence.md).
- Sass or compiled CSS. Branch `prototype/bs5-sass-vs-compiled` at `ee94e16c`. 16 Sass variables against 209 hand-written declarations for the same pixels. See [Sass build or compiled CSS](issues/02-sass-or-compiled.md).
- Clean room or codemod. Branch `prototype/bs5-clean-room-vs-codemod` at `c92caf96`. 14 app rules and no colour literals against 119 to 146 rules and 50 to 60 literals. See [Clean room or codemod, tried on the conversation page](issues/04-clean-room-or-codemod.md).
- Before screenshots. Branch `research/before-screenshots` at `9cc072f7`. 42 images in the ignored `.scratch/bootstrap5/before/2026-09-27/`.
- Research. Branches `research/bs5-branded-sites` (`ce3f028d`), `research/bs5-modal-vs-auth0-lock` (`5367b291`), `research/bs5-foreign-html-classes` (`49aa8426`), `research/bs5-rename-list` (`f8a511ef`) and `research/bs5-mentions-autocomplete` (`1914e1b6`).
- Unproven. Signed-in views were never prototyped, so family PRs will be larger than the guest-only prototype. Screen-reader behaviour of `aria-activedescendant` on a textarea is untested until BS5-16.

## Appendix B. Alternatives rejected

- Loading both frameworks on one page, a per-page switch in one base, shared includes first, and a long-lived branch. See the coexistence ticket.
- Compiled Bootstrap with hand-written overrides, and Sass in a Docker build stage. See the Sass ticket.
- A codemod pass, which kept 50 to 60 colour literals per page and broke dark mode.
- Fork-then-port for scripts, a bundler, and Tribute.js or `@textcomplete` for mentions.
- An SVG sprite, the icon font and CSS masks for icons.
- Keeping today's breakpoints by bumping every column tier.

## Appendix C. Risks

- The template dual-copy rule. A fix to a copied family must land in both trees until BS5-18. Owners check `core/templates/` for changes on trunk at every rebase.
- Cloudflare challenges headless browsers on live Sites, so all live lanes render locally. A lane that needs the live Site is a manual operator check.
- Legacy `*.microco.sm` background URLs never answer. The harness rewrites them. The production bug stays outside this plan.
- `/search/?q=` without `defaults=true` returns 500 on production. Outside this plan, but BS5-10 must not rely on it.
- Dart Sass 3 removes `@import`, which Bootstrap 5.3 needs. `bin/build-css` pins 1.x.
- The mentions autocomplete is our own `core/static/js/bs5/mentions.js` (operator confirmed 2026-09-28). If hand-rolled caret positioning proves fragile in BS5-08, vendor `dom-input-range` for that step only, per the mentions research.
- The harness user is the operator's real account `duncs`. Checks that post, edit, delete, RSVP or change settings act on live lfgss data, so they run only against the self-huddle 3310071 or a conversation the operator names for testing, record once, and replay after. Recording signed-in GETs can mark items as read.
- No `control-ui`, `swarm` or cloud VMs exist here. Lanes run as local subagents with Playwright, and throughput is lower than the template assumes.

## Appendix D. Links and reading list

- `.scratch/bootstrap5/map.md`, the decision index, and every ticket it links.
- `docs/BOOTSTRAP5-HANDOFF.md`, the requirement and the measured starting point.
- `CLAUDE.md` and `CONTEXT.md` for architecture and the terms Color mode, Site branding and Site theme.
- The tolerance checklist in [How close is close enough](issues/05-close-enough.md), which every review-gated PR is judged against.
- The Bootstrap 5.3 migration guide and color modes docs.
