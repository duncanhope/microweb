// The comment box (BS5-08): forms/block_comment_box.html, marked data-mw-editor.
// Ported from js/simpleEditor.js and the parts of Markdown.Editor.js it used,
// without jQuery: the formatting toolbar and its Ctrl shortcuts, Preview,
// Ctrl+Enter to post, @mentions (mentions.js), attachments (attachments.js)
// and the check before posting, which replaces formValidator.js with the
// Constraint Validation API and Bootstrap's .is-invalid.
//
// comments.js, the family's page script, calls initEditors(): every comment
// box on the page and every form marked data-mw-validate.

import { Attachments } from './attachments.js';
import { attachMentions, replaceText } from './mentions.js';

export const API_BASE = document.querySelector('meta[name="subdomain"]')?.content || '';

// ---------------------------------------------------------------------------
// Quoting

// The page's selected text, or ''.
export function selectedText() {
  return (window.getSelection()?.toString() || '').trim();
}

// Each line as a Markdown quote.
export function quoteText(text) {
  return text.replace(/\r\n?/g, '\n').split('\n').map((line) => '> ' + line).join('\n');
}

// The newlines that make text end in a blank line ('' for no text).
const blankLineAfter = (text) => (text ? '\n\n'.slice(/\n{0,2}$/.exec(text)[0].length) : '');

// ---------------------------------------------------------------------------
// The check before posting

// Required fields must hold more than spaces; the first invalid field gets focus.
export function validateOnSubmit(form) {
  form.addEventListener('submit', (event) => {
    const fields = [...form.elements].filter((field) => field.willValidate);
    for (const field of fields) {
      if (field.required && 'value' in field) field.setCustomValidity(field.value.trim() ? '' : 'empty');
      field.classList.toggle('is-invalid', !field.validity.valid);
    }
    const invalid = fields.find((field) => !field.validity.valid);
    if (invalid) {
      event.preventDefault();
      event.stopImmediatePropagation();
      invalid.focus();
    }
  });
  form.addEventListener('input', (event) => {
    const field = event.target;
    if (field.classList.contains('is-invalid') && field.value.trim()) {
      field.setCustomValidity('');
      field.classList.remove('is-invalid');
    }
  });
}

// ---------------------------------------------------------------------------
// Preview: Markdown.Converter.js (Pagedown) loads on first use.

let converter;

function loadConverter() {
  converter ??= new Promise((resolve, reject) => {
    const ready = () => resolve(new window.Markdown.Converter());
    if (window.Markdown?.Converter) return ready();
    const script = document.createElement('script');
    script.src = new URL('../Markdown.Converter.js', import.meta.url);
    script.onload = ready;
    script.onerror = () => { converter = null; reject(new Error('Markdown.Converter.js did not load')); };
    document.head.append(script);
  });
  return converter;
}

// The preview shows the member's own text, which may quote others. Drop
// anything that could run script; the API sanitises the real comment.
const UNSAFE = 'script, style, iframe, object, embed, form, link, meta, base';

function safeNodes(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  for (const el of doc.body.querySelectorAll(UNSAFE)) el.remove();
  for (const el of doc.body.querySelectorAll('*')) {
    for (const { name, value } of [...el.attributes]) {
      if (name.startsWith('on') || (/^(href|src|action|formaction)$/.test(name) && /^\s*(javascript|data):/i.test(value))) {
        el.removeAttribute(name);
      }
    }
  }
  return [...doc.body.childNodes];
}

// ---------------------------------------------------------------------------
// The editor

// Ctrl (or Cmd) + key, as Pagedown bound them.
const SHORTCUTS = { b: 'bold', i: 'italic', l: 'link', q: 'quote', k: 'code', g: 'image', o: 'list' };

export class SimpleEditor {
  constructor(root) {
    this.root = root;
    root.mwEditor = this;
    this.textarea = root.querySelector('textarea');
    if (!this.textarea) return; // a guest's box: a sign-in button and a disabled toolbar
    this.form = root.querySelector('form');
    this.preview = root.querySelector('.mw-editor-preview');
    this.previewButton = root.querySelector('[data-mw-preview]');

    root.querySelector('.mw-editor-toolbar').addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      if (button === this.previewButton) this.togglePreview();
      else this.format(button.dataset.mwFormat);
    });
    this.textarea.addEventListener('keydown', (event) => this.onKeydown(event));

    if (this.form) {
      validateOnSubmit(this.form);
      this.form.addEventListener('reset', () => {
        this.showPreview(false);
        this.textarea.classList.remove('is-invalid');
        this.attachments?.clear();
      });
    }

    attachMentions(this.textarea, { apiBase: API_BASE });

    const files = root.querySelector('[data-mw-attachments]');
    if (files) {
      this.attachments = new Attachments(files, {
        form: this.form || root.closest('form'),
        apiBase: API_BASE,
        source: root.dataset.source,
        count: parseInt(root.dataset.numAttachments, 10) || 0,
      });
    }
  }

  onKeydown(event) {
    if (!(event.ctrlKey || event.metaKey) || event.altKey || event.isComposing) return;
    if (event.key === 'Enter') {
      event.preventDefault();
      this.form?.requestSubmit();
      return;
    }
    const command = !event.shiftKey && SHORTCUTS[event.key.toLowerCase()];
    if (command) {
      event.preventDefault();
      this.format(command);
    }
  }

  // Replace [start, end) with text, then select [selStart, selEnd).
  replace(start, end, text, selStart = start + text.length, selEnd = selStart) {
    replaceText(this.textarea, start, end, text);
    this.textarea.setSelectionRange(selStart, selEnd);
  }

  format(command) {
    this.showPreview(false);
    switch (command) {
      case 'bold': return this.stars(2, 'strong text');
      case 'italic': return this.stars(1, 'emphasized text');
      case 'link': return this.link(false);
      case 'image': return this.link(true);
      case 'list': return this.lines((i) => `${i + 1}. `, /^\d+\.\s/, 'List item');
      case 'quote': return this.lines(() => '> ', /^>\s?/, 'Quote');
      case 'code': return this.code();
    }
  }

  // Bold and italics: a toggle, as in Pagedown. Italics inside bold adds stars.
  stars(count, placeholder) {
    const { value, selectionStart: start, selectionEnd: end } = this.textarea;
    const around = Math.min(/\**$/.exec(value.slice(0, start))[0].length, /^\**/.exec(value.slice(end))[0].length);
    if (around >= count && !(around === 2 && count === 1)) {
      const inner = value.slice(start, end);
      this.replace(start - count, end + count, inner, start - count, end - count);
      return;
    }
    // Spaces at either end of the selection stay outside the stars.
    const [, lead, body, trail] = /^(\s*)([\s\S]*?)(\s*)$/.exec(value.slice(start, end));
    const inner = body || placeholder;
    const marker = '*'.repeat(count);
    const at = start + lead.length + count;
    this.replace(start, end, lead + marker + inner + marker + trail, at, at + inner.length);
  }

  // Links and images ask for the address. The selection becomes the text.
  link(image) {
    const { value, selectionStart: start, selectionEnd: end } = this.textarea;
    const url = window.prompt(image ? 'Enter or paste your image link here' : 'Enter your link here', '');
    if (!url || !url.trim()) return;
    const label = value.slice(start, end).replace(/[[\]]/g, '\\$&') || (image ? '' : url.trim());
    const open = image ? '![' : '[';
    this.replace(start, end, `${open}${label}](${url.trim()})`, start + open.length, start + open.length + label.length);
  }

  // The start and end of the whole lines the selection touches.
  lineBounds() {
    const { value, selectionStart: start, selectionEnd: end } = this.textarea;
    const from = value.lastIndexOf('\n', start - 1) + 1;
    const stop = end > start && value[end - 1] === '\n' ? end - 1 : end;
    const to = value.indexOf('\n', stop);
    return [from, to === -1 ? value.length : to];
  }

  // Lists and quotes prefix every selected line, on a block of its own; again removes them.
  lines(prefix, pattern, placeholder) {
    const { value } = this.textarea;
    const [from, to] = this.lineBounds();
    const block = value.slice(from, to);
    const rows = block.split('\n');
    if (block.trim() && rows.every((row) => !row.trim() || pattern.test(row))) {
      const plain = rows.map((row) => row.replace(pattern, '')).join('\n');
      this.replace(from, to, plain, from, from + plain.length);
      return;
    }
    const text = (block.trim() ? rows : [placeholder]).map((row, i) => prefix(i) + row).join('\n');
    const before = from > 0 && value.slice(0, from).trim() && !value.slice(0, from).endsWith('\n\n') ? '\n' : '';
    const after = value.slice(to).startsWith('\n\n') || !value.slice(to).trim() ? '' : '\n';
    const selStart = from + before.length;
    this.replace(from, to, before + text + after, selStart, selStart + text.length);
  }

  // Code: a fenced block, after a blank line as Markdown needs; again removes the fence.
  code() {
    const { value, selectionStart: start, selectionEnd: end } = this.textarea;
    if (value.slice(start - 4, start) === '```\n' && value.slice(end, end + 4) === '\n```') {
      const inner = value.slice(start, end);
      this.replace(start - 4, end + 4, inner, start - 4, start - 4 + inner.length);
      return;
    }
    const inner = value.slice(start, end) || 'enter code here';
    const before = blankLineAfter(value.slice(0, start));
    const after = value.slice(end).startsWith('\n') || end === value.length ? '' : '\n';
    const text = `${before}\`\`\`\n${inner}\n\`\`\`${after}`;
    const selStart = start + before.length + 4;
    this.replace(start, end, text, selStart, selStart + inner.length);
  }

  // Quote text at the end of the box, then leave the caret after it.
  insertQuote(text) {
    const { value } = this.textarea;
    this.replace(value.length, value.length, blankLineAfter(value) + quoteText(text) + '\n\n');
  }

  async togglePreview() {
    const show = this.preview.hidden;
    if (show) {
      const body = this.preview.querySelector('[data-mw-preview-body]');
      try {
        body.replaceChildren(...safeNodes((await loadConverter()).makeHtml(this.textarea.value)));
      } catch {
        body.textContent = 'The preview is not available right now.';
      }
      this.preview.style.minHeight = this.textarea.offsetHeight + 'px';
    }
    this.showPreview(show);
    if (!show) this.textarea.focus();
  }

  showPreview(show) {
    if (!this.preview) return;
    this.preview.hidden = !show;
    this.textarea.hidden = show;
    this.previewButton.setAttribute('aria-pressed', String(show));
  }
}

// ---------------------------------------------------------------------------

// Wire the page's comment boxes (those not already wired) and checked forms.
export function initEditors() {
  for (const root of document.querySelectorAll('[data-mw-editor]')) {
    if (!root.mwEditor) new SimpleEditor(root);
  }
  for (const form of document.querySelectorAll('form[data-mw-validate]')) validateOnSubmit(form);
}
