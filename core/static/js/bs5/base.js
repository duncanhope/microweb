// Shared behaviour for every Bootstrap 5 page, loaded by core/templates_bs5/base.html.
// Ported from js/base.js without jQuery or moment.js: relative times on <time>,
// short stat numbers, code highlighting, the pagination page jump and tooltips.
// It also loads prettify.js and metabar.js, only on pages that need them.
// Bootstrap is the classic-script bundle, so it is window.bootstrap here.

const { bootstrap } = window;
const LOCALE = document.documentElement.lang || 'en';

// ---------------------------------------------------------------------------
// Relative times on <time datetime="...">. <time class="plain"> is left alone.
// Clicking any time swaps every time between relative and absolute.

const relative = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'always' });
const justNow = new Intl.RelativeTimeFormat(LOCALE, { numeric: 'auto' });
const precise = new Intl.DateTimeFormat(LOCALE, {
  weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
});

// The same buckets as moment.js's fromNow, which this replaces: under 45
// seconds is "now", under 45 minutes counts minutes, under 22 hours counts
// hours, under 26 days counts days, under 11 months counts months.
export function relativeTime(date, now = Date.now()) {
  const delta = date.getTime() - now;
  const sign = delta < 0 ? -1 : 1;
  const seconds = Math.round(Math.abs(delta) / 1000);
  const minutes = Math.round(seconds / 60);
  const hours = Math.round(minutes / 60);
  const days = Math.round(hours / 24);
  const months = Math.round(days * 4800 / 146097);
  const years = Math.round(months / 12);

  if (seconds < 45) return justNow.format(0, 'second');
  const [value, unit] =
    minutes < 45 ? [Math.max(minutes, 1), 'minute'] :
    hours < 22 ? [Math.max(hours, 1), 'hour'] :
    days < 26 ? [Math.max(days, 1), 'day'] :
    months < 11 ? [Math.max(months, 1), 'month'] :
    [Math.max(years, 1), 'year'];
  return relative.format(sign * value, unit);
}

let showAbsolute = false;

export function updateTimes(root = document) {
  const now = Date.now();
  for (const time of root.querySelectorAll('time[datetime]:not(.plain)')) {
    const date = new Date(time.dateTime);
    if (Number.isNaN(date.getTime())) continue;
    const [text, title] = showAbsolute
      ? [precise.format(date), relativeTime(date, now)]
      : [relativeTime(date, now), precise.format(date)];
    if (time.textContent !== text) time.textContent = text;
    if (time.title !== title) time.title = title;
  }
}

document.addEventListener('click', (event) => {
  const time = event.target.closest('time');
  // Event dates in the event header and list are links and pills, not toggles.
  if (!time || time.classList.contains('plain') || time.closest('.pills-event, .cell-meta-event')) return;
  showAbsolute = !showAbsolute;
  updateTimes();
});

updateTimes();
setInterval(() => { if (!document.hidden) updateTimes(); }, 60000);

// ---------------------------------------------------------------------------
// Stats: 1234567 becomes 1.23M, with the full figure in the tooltip.

const SI = [[1e18, 'E'], [1e15, 'P'], [1e12, 'T'], [1e9, 'G'], [1e6, 'M'], [1e3, 'k']];

export function shortNumber(num, digits = 2) {
  const trim = (s) => s.replace(/\.0+$|(\.[0-9]*[1-9])0+$/, '$1');
  for (const [value, symbol] of SI) {
    if (num >= value) return trim((num / value).toFixed(digits)) + symbol;
  }
  return trim(num.toFixed(digits));
}

for (let el of document.querySelectorAll('span[stat]')) {
  const num = parseInt(el.getAttribute('stat'), 10);
  if (!(num >= 1000)) continue;
  // The tooltip is the whole stat, such as "1,008 comments".
  const tooltip = el.parentElement.textContent.replace(/\s+/g, ' ').trim();
  // The number may sit inside a link, such as a search for the items.
  while (el.firstElementChild && el.firstChild === el.firstElementChild) {
    el = el.firstElementChild;
  }
  el.title = tooltip;
  el.textContent = shortNumber(num);
}

// ---------------------------------------------------------------------------
// Code blocks: prettify.js highlights pre > code. Most pages have none, so
// the script loads only when there is something to highlight.

const PRETTIFY_LANGS = new Set(['bsh', 'c', 'cc', 'cpp', 'cs', 'csh', 'cyc', 'cv', 'htm', 'html', 'java', 'js',
  'm', 'mxml', 'perl', 'pl', 'pm', 'py', 'rb', 'sh', 'xhtml', 'xml', 'xsl']);

const codeBlocks = document.querySelectorAll('pre > code');
for (const code of codeBlocks) {
  const pre = code.parentElement;
  code.classList.add('prettyprint');
  pre.classList.add('prettyprint', 'linenums');
  const lang = pre.getAttribute('lang');
  if (PRETTIFY_LANGS.has(lang)) pre.classList.add('lang-' + lang);
}
if (codeBlocks.length) {
  const script = document.createElement('script');
  script.src = new URL('../../3rd/prettify/r298/prettify.js', import.meta.url);
  script.onload = () => window.prettyPrint();
  document.head.append(script);
}

// ---------------------------------------------------------------------------
// Pagination: jump to a page number. The form carries data-initial (this
// page), data-limit (items per page) and data-max (pages); leaving the field
// submits it.

document.addEventListener('submit', (event) => {
  const form = event.target;
  if (form.name !== 'paginationByOffset') return;
  const { initial, limit, max } = form.dataset;
  const value = parseInt(form.querySelector('input:not([type=hidden])').value, 10);
  if (Number.isNaN(value) || value < 1 || value > Number(max) || value === Number(initial)) {
    event.preventDefault();
    return;
  }
  form.elements.offset.value = Number(limit) * (value - 1);
});

document.addEventListener('focusout', (event) => {
  const field = event.target;
  if (field.form && field.form.name === 'paginationByOffset' && field.type !== 'hidden') {
    field.form.requestSubmit();
  }
});

// ---------------------------------------------------------------------------
// Tooltips: <a data-bs-toggle="tooltip" title="...">.

export function initTooltips(root = document) {
  for (const el of root.querySelectorAll('[data-bs-toggle="tooltip"]')) {
    bootstrap.Tooltip.getOrCreateInstance(el, { container: 'body' });
  }
}

initTooltips();

// ---------------------------------------------------------------------------
// The Follow control, on pages that have one.

if (document.querySelector('[data-mw-subscribe]')) import('./metabar.js');
