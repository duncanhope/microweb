// Comment boxes on the conversation and single-comment pages (BS5-08).
// Ported from js/comments.js and the inline scripts of conversation.html and
// comment.html, without jQuery.
//
// The page marks its comments with data-mw-comments. Inside it:
// - [data-mw-reply] buttons (Reply and Edit, block_comment_single.html) open
//   a copy of the comment box under their comment; clicking again, or
//   Cancel, closes it. Only one is open at a time, and while it is open the
//   reply box at the foot of the page ([data-mw-reply-default]) is hidden.
//   Reply quotes the selected text. Edit loads the comment's Markdown.
// - The box is copied from template[data-mw-reply-template], or else from
//   the reply box at the foot of the page, before anything is typed in it.
// - data-mw-open-highlighted opens the highlighted comment's box on load
//   (comment.html): Reply, or Edit when the comment is the member's own.
// Post a reply in the metabar (#post-a-reply-handle) quotes the selected
// text into the reply box at the foot of the page.
//
// It is the family's page script: forms/conversation.html loads it too, for
// its comment box and its check before posting (simpleEditor.js initEditors).

import { SimpleEditor, initEditors, selectedText } from './simpleEditor.js';

class Comments {
  constructor(root) {
    this.root = root;
    this.replyBox = root.querySelector('[data-mw-reply-default]');
    const template = root.querySelector('template[data-mw-reply-template]');
    const source = template ? template.content : this.replyBox;
    this.template = source?.querySelector('[data-mw-editor]')?.cloneNode(true);
    this.open = null;
    this.selection = '';

    // A click can clear the selection before the click event, so keep it from pointerdown.
    document.addEventListener('pointerdown', (event) => {
      if (event.target.closest('[data-mw-reply], #post-a-reply-handle')) this.selection = selectedText();
    });
    root.addEventListener('click', (event) => {
      const button = event.target.closest('[data-mw-reply]');
      if (button) this.toggle(button);
    });
    root.addEventListener('reset', (event) => {
      if (this.open?.box.contains(event.target)) this.close();
    });

    const handle = document.getElementById('post-a-reply-handle');
    if (handle && this.replyBox) handle.addEventListener('click', (event) => this.replyToPage(event));

    if (root.hasAttribute('data-mw-open-highlighted')) {
      // Reply comes before Edit, so this is Reply when there is one.
      const button = root.querySelector('.mw-comments-highlighted [data-mw-reply]');
      if (button) this.openBox(button, { focus: false });
    }
  }

  takeSelection() {
    const text = this.selection || selectedText();
    this.selection = '';
    return text;
  }

  toggle(button) {
    const wasOpen = this.open?.button === button;
    const quote = this.takeSelection();
    this.close();
    if (!wasOpen) this.openBox(button, { quote });
  }

  openBox(button, { quote = '', focus = true } = {}) {
    if (!this.template) return;
    const { action, ref, commentId, source, numAttachments } = button.dataset;
    const editor = this.template.cloneNode(true);
    editor.dataset.source = source || '';
    editor.dataset.numAttachments = numAttachments || '0';
    const form = editor.querySelector('form');
    form.action = action;
    form.elements.namedItem('id').value = commentId || '';
    form.elements.namedItem('inReplyTo').value = ref || '';

    const box = document.createElement('div');
    box.className = 'mw-comment-box';
    box.append(editor);
    button.closest('.mw-comment-actions').after(box);
    button.setAttribute('aria-expanded', 'true');
    if (this.replyBox) this.replyBox.hidden = true;

    const simple = new SimpleEditor(editor);
    this.open = { button, box };
    if (source) {
      form.querySelector('[data-mw-submit]').textContent = 'Save changes';
      this.loadMarkdown(simple.textarea, source);
    } else if (ref && quote) {
      simple.insertQuote(quote);
    }
    if (focus) simple.textarea.focus();
  }

  // Edit: fill the box with the comment's Markdown.
  async loadMarkdown(textarea, source) {
    const placeholder = textarea.placeholder;
    textarea.placeholder = 'Loading... Please wait...';
    try {
      const response = await fetch(source + 'source/', { credentials: 'same-origin' });
      if (response.ok) textarea.value = (await response.json()).data.markdown;
    } catch {
      // Leave the box empty; the member can still type.
    }
    textarea.placeholder = placeholder;
  }

  close() {
    if (!this.open) return;
    this.open.box.remove();
    this.open.button.setAttribute('aria-expanded', 'false');
    this.open = null;
    if (this.replyBox) this.replyBox.hidden = false;
  }

  // Post a reply (#post-a-reply-handle, a link to #reply): quote the selection
  // into the reply box and focus it. The link's own jump would take the focus
  // away again, so it is done here. On narrow screens the metabar drawer
  // closes first.
  replyToPage(event) {
    event.preventDefault();
    const quote = this.takeSelection();
    this.close();
    const editor = this.replyBox.querySelector('[data-mw-editor]').mwEditor;
    if (quote) editor.insertQuote(quote);
    if (location.hash !== '#reply') history.pushState(null, '', '#reply');
    const focus = () => {
      this.replyBox.scrollIntoView();
      editor.textarea.focus({ preventScroll: true });
    };
    const drawer = document.getElementById('mw-metabar');
    const offcanvas = drawer && window.bootstrap?.Offcanvas.getInstance(drawer);
    if (offcanvas && drawer.classList.contains('show')) {
      // Bootstrap focuses the drawer button once the drawer has gone; focus the box after that.
      drawer.addEventListener('hidden.bs.offcanvas', focus, { once: true });
      offcanvas.hide();
    } else {
      focus();
    }
  }
}

// Comments copies the reply box before initEditors wires it.
const root = document.querySelector('[data-mw-comments]');
if (root) new Comments(root);
initEditors();
