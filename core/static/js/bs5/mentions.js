// @mentions in comment boxes (BS5-08). Replaces jquery.textcomplete (ticket 14).
//
// Typing @ or + after a space starts a mention. The members whose names
// start with what follows are fetched from the Site's API (anonymously, as
// today) and up to five are listed under the caret. Up and Down move the
// active member, Enter or Tab inserts "@name ", Escape closes the list.
//
// The textarea keeps its textbox role (a combobox role is not allowed on a
// textarea) and gets aria-autocomplete, aria-controls and
// aria-activedescendant, the APG combobox pattern adapted to a textarea. A
// visually hidden status line announces how many members were found.

// The Site's API, which member searches ask: <meta name="subdomain"> in the base.
export const API_BASE = document.querySelector('meta[name="subdomain"]')?.content || '';

const TRIGGER = /(?:^|[^\w])([@+])([^\s@+]{0,25})$/;
const LIMIT = 5;
const DEBOUNCE_MS = 150;

const cache = new Map();

// Replace [start, end) of a textarea with text. insertText keeps the
// browser's own undo; setRangeText is the fallback. Either way an input
// event follows, as after typing.
export function replaceText(textarea, start, end, text) {
  textarea.focus();
  textarea.setSelectionRange(start, end);
  if (!document.execCommand('insertText', false, text)) {
    textarea.setRangeText(text, start, end, 'end');
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }
}

// Members whose profile name starts with term, most active first.
export async function searchProfiles(apiBase, term, { signal } = {}) {
  const key = term.toLowerCase();
  if (!cache.has(key)) {
    const url = `${apiBase}/api/v1/profiles?disableBoiler&top=true&limit=${LIMIT}&q=${encodeURIComponent(term)}`;
    const response = await fetch(url, { signal, credentials: 'omit' });
    if (!response.ok) throw new Error('Profile search failed: ' + response.status);
    const items = (await response.json()).profiles?.items || [];
    cache.set(key, items.filter((p) => p.profileName.toLowerCase().startsWith(key)).slice(0, LIMIT));
  }
  return cache.get(key);
}

// The member searches of one box (the mentions here, the event form's
// invite box), one at a time: each search aborts the one before it, and only
// the latest may answer. search() resolves to the members found, or to null
// when a later search or cancel() has overtaken it, and rejects only when it
// is still the latest and failed. A failure is for the box to show, never a
// reason to cancel: a search typed since may be waiting out its debounce.
export class ProfileSearch {
  constructor(apiBase) {
    this.apiBase = apiBase;
    this.controller = null;
  }

  // A search has started and neither answered nor been cancelled.
  get pending() {
    return this.controller !== null;
  }

  async search(term) {
    this.controller?.abort();
    const controller = this.controller = new AbortController();
    let found;
    try {
      found = await searchProfiles(this.apiBase, term, { signal: controller.signal });
    } catch (error) {
      if (controller !== this.controller) return null;
      this.controller = null;
      throw error;
    }
    if (controller !== this.controller) return null;
    this.controller = null;
    return found;
  }

  cancel() {
    this.controller?.abort();
    this.controller = null;
  }
}

// ---------------------------------------------------------------------------
// Where the caret is, measured with a hidden copy of the textarea.

const MIRRORED = [
  'boxSizing', 'width', 'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
  'borderStyle', 'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft', 'fontStyle', 'fontVariant',
  'fontWeight', 'fontStretch', 'fontSize', 'lineHeight', 'fontFamily', 'textAlign', 'textTransform',
  'textIndent', 'letterSpacing', 'wordSpacing', 'tabSize', 'direction',
];

function caretOffset(textarea, index) {
  const style = getComputedStyle(textarea);
  const mirror = document.createElement('div');
  for (const name of MIRRORED) mirror.style[name] = style[name];
  Object.assign(mirror.style, {
    position: 'absolute', top: '0', left: '-9999px', visibility: 'hidden', overflow: 'hidden',
    whiteSpace: 'pre-wrap', overflowWrap: 'break-word',
  });
  mirror.textContent = textarea.value.slice(0, index);
  const marker = document.createElement('span');
  marker.textContent = '​';
  mirror.append(marker);
  document.body.append(mirror);
  const offset = {
    top: marker.offsetTop - textarea.scrollTop,
    left: marker.offsetLeft - textarea.scrollLeft,
    height: parseFloat(style.lineHeight) || marker.offsetHeight,
  };
  mirror.remove();
  return offset;
}

// ---------------------------------------------------------------------------

let count = 0;

class Mentions {
  constructor(textarea, apiBase) {
    this.textarea = textarea;
    this.apiBase = apiBase;
    this.searches = new ProfileSearch(apiBase);
    this.id = 'mw-mentions-' + ++count;
    this.results = [];
    this.active = -1;
    this.match = null;
    this.composing = false;

    this.list = document.createElement('ul');
    Object.assign(this.list, { id: this.id, className: 'dropdown-menu mw-mentions' });
    this.list.setAttribute('role', 'listbox');
    this.list.setAttribute('aria-label', 'Mention suggestions');
    this.status = document.createElement('div');
    this.status.className = 'visually-hidden';
    this.status.setAttribute('role', 'status');
    textarea.after(this.list, this.status);

    textarea.setAttribute('aria-autocomplete', 'list');
    textarea.setAttribute('aria-haspopup', 'listbox');
    textarea.setAttribute('aria-controls', this.id);

    textarea.addEventListener('input', () => this.update());
    textarea.addEventListener('keydown', (event) => this.onKeydown(event));
    textarea.addEventListener('keyup', (event) => {
      if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) this.update();
    });
    textarea.addEventListener('compositionstart', () => { this.composing = true; });
    textarea.addEventListener('compositionend', () => { this.composing = false; this.update(); });
    textarea.addEventListener('blur', () => this.close());
    // Keep focus in the textarea while the pointer picks a member.
    this.list.addEventListener('mousedown', (event) => event.preventDefault());
    this.list.addEventListener('click', (event) => {
      const option = event.target.closest('[role=option]');
      if (option) this.commit(Number(option.dataset.index));
    });
    this.list.addEventListener('mousemove', (event) => {
      const option = event.target.closest('[role=option]');
      if (option) this.setActive(Number(option.dataset.index));
    });
  }

  get isOpen() {
    return this.list.classList.contains('show');
  }

  // The mention being typed before the caret, or null.
  current() {
    const { value, selectionStart, selectionEnd } = this.textarea;
    if (selectionStart !== selectionEnd) return null;
    const found = TRIGGER.exec(value.slice(0, selectionEnd));
    if (!found) return null;
    const [, symbol, term] = found;
    return { symbol, term, start: selectionEnd - term.length - 1, end: selectionEnd };
  }

  update() {
    if (this.composing) return;
    const match = this.current();
    this.match = match;
    clearTimeout(this.timer);
    if (!match) {
      if (this.isOpen || this.searches.pending) this.close();
      return;
    }
    if (this.isOpen) this.narrow(match);
    this.timer = setTimeout(() => this.search(match), DEBOUNCE_MS);
  }

  // Until the API answers for what is typed now, show only the members
  // already listed who still match it, so Enter never picks one who doesn't.
  narrow(match) {
    const term = match.term.toLowerCase();
    const kept = this.results.filter((profile) => profile.profileName.toLowerCase().startsWith(term));
    if (kept.length === this.results.length) return;
    this.results = kept;
    if (kept.length) this.render();
    else this.hide();
  }

  async search(match) {
    let results;
    try {
      results = await this.searches.search(match.term);
    } catch {
      this.hide();
      return;
    }
    // Only the latest search for the mention still being typed may show.
    if (!results || this.match !== match) return;
    this.results = results;
    if (!results.length) {
      this.hide();
      this.announce('No matching members');
      return;
    }
    this.render();
    this.announce(`${results.length} suggestion${results.length === 1 ? '' : 's'}, use up and down to choose`);
  }

  render() {
    this.list.replaceChildren(...this.results.map((profile, index) => {
      const option = document.createElement('li');
      option.id = `${this.id}-${index}`;
      option.className = 'dropdown-item';
      option.dataset.index = String(index);
      option.setAttribute('role', 'option');
      const avatar = document.createElement('img');
      avatar.alt = '';
      avatar.width = avatar.height = 20;
      avatar.src = new URL(profile.avatar || '/static/img/avatar.gif', this.apiBase || location.href).href;
      option.append(avatar, document.createTextNode(this.match.symbol + profile.profileName));
      return option;
    }));
    this.list.classList.add('show');
    // The options are new: highlight the first even if the old first was.
    this.active = -1;
    this.setActive(0);
    this.place();
  }

  // Under the caret, or above it when there is no room below.
  place() {
    const ta = this.textarea;
    if (this.caret?.start !== this.match.start) this.caret = { start: this.match.start, ...caretOffset(ta, this.match.start) };
    const { caret } = this;
    const top = ta.offsetTop + ta.clientTop + caret.top;
    const left = Math.max(0, Math.min(ta.offsetLeft + ta.clientLeft + caret.left, ta.offsetLeft + ta.offsetWidth - this.list.offsetWidth));
    this.list.style.left = left + 'px';
    this.list.style.top = top + caret.height + 'px';
    if (this.list.getBoundingClientRect().bottom > window.innerHeight && top - this.list.offsetHeight > 0) {
      this.list.style.top = top - this.list.offsetHeight + 'px';
    }
  }

  setActive(index) {
    const options = this.list.children;
    index = (index + options.length) % options.length;
    if (index === this.active) return;
    this.active = index;
    for (const [i, option] of [...options].entries()) {
      option.classList.toggle('active', i === this.active);
      option.setAttribute('aria-selected', String(i === this.active));
    }
    this.textarea.setAttribute('aria-activedescendant', options[this.active].id);
    options[this.active].scrollIntoView({ block: 'nearest' });
  }

  onKeydown(event) {
    if (!this.isOpen || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
    switch (event.key) {
      case 'ArrowDown':
        this.setActive(this.active + 1);
        break;
      case 'ArrowUp':
        this.setActive(this.active - 1);
        break;
      case 'Enter':
      case 'Tab':
        this.commit(this.active);
        break;
      case 'Escape':
        // Stop here, so a modal around the box stays open.
        event.stopPropagation();
        this.close();
        break;
      default:
        return;
    }
    event.preventDefault();
  }

  commit(index) {
    const profile = this.results[index];
    const match = this.current();
    this.close();
    if (!profile || !match) return;
    replaceText(this.textarea, match.start, match.end, match.symbol + profile.profileName + ' ');
  }

  // Stop any search, and hide the list.
  close() {
    clearTimeout(this.timer);
    this.searches.cancel();
    this.hide();
  }

  // Hide the list only: a search typed since may still be on its way.
  hide() {
    this.caret = null;
    this.list.classList.remove('show');
    this.list.replaceChildren();
    this.textarea.removeAttribute('aria-activedescendant');
    this.active = -1;
  }

  announce(text) {
    this.status.textContent = text;
  }
}

// Mentions for one textarea. apiBase is the Site's API origin, from <meta name="subdomain">.
export function attachMentions(textarea, { apiBase = '' } = {}) {
  textarea.mwMentions ??= new Mentions(textarea, apiBase);
  return textarea.mwMentions;
}
