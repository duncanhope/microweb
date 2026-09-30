// The avatar picker on the profile form (BS5-09): forms/profile.html, marked
// data-mw-avatar. Ported from js/profilePicture.js without jQuery.
// Choosing an image, or dropping one on the box, shows it in the box before
// the form is saved; nothing is uploaded until then. A file that is not an
// image is refused: the field is emptied and the box, as on Cancel (the
// form's reset), shows the picture the page loaded with.

export class AvatarPicker {
  constructor(root) {
    this.input = root.querySelector('input[type=file]');
    this.drop = root.querySelector('[data-mw-avatar-drop]');
    this.preview = this.drop.querySelector('img');
    this.original = { src: this.preview.getAttribute('src'), shown: !this.preview.hidden };
    this.objectUrl = null;

    this.input.addEventListener('change', () => this.show(this.input.files));
    this.drop.addEventListener('dragover', (event) => {
      event.preventDefault();
      this.drop.classList.add('is-dragover');
    });
    this.drop.addEventListener('dragleave', () => this.drop.classList.remove('is-dragover'));
    this.drop.addEventListener('drop', (event) => {
      event.preventDefault();
      this.drop.classList.remove('is-dragover');
      const { files } = event.dataTransfer;
      if (isImage(files[0])) this.input.files = files;
      this.show(files);
    });
    // The form's reset clears the file field; the box follows once it has.
    root.closest('form')?.addEventListener('reset', () => setTimeout(() => this.restore()));
  }

  show(files) {
    const file = files?.[0];
    if (!isImage(file)) {
      this.input.value = '';
      this.restore();
      return;
    }
    this.release();
    this.objectUrl = URL.createObjectURL(file);
    this.setPicture(this.objectUrl);
  }

  restore() {
    this.release();
    this.setPicture(this.original.shown ? this.original.src : null);
  }

  setPicture(src) {
    if (src) this.preview.src = src;
    else this.preview.removeAttribute('src');
    this.preview.hidden = !src;
    this.drop.classList.toggle('has-image', !!src);
  }

  release() {
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = null;
  }
}

function isImage(file) {
  return !!file && file.type.startsWith('image/');
}

for (const root of document.querySelectorAll('[data-mw-avatar]')) {
  new AvatarPicker(root);
}
