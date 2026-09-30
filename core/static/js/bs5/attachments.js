// A comment box's attachments (BS5-08), ported from js/attachments.js and the
// gallery half of js/simpleEditor.js without jQuery.
//
// Pick or drop files; they are listed (images as thumbnails) and can be
// removed before posting. The file input always holds exactly the listed
// files. When a comment is edited, its saved attachments are fetched and
// listed too; removing one adds its hash to a hidden attachments-delete
// field, which the comment views read.

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'gif', 'png', 'bmp']);

const sameFile = (a, b) => a.name === b.name && a.size === b.size && a.lastModified === b.lastModified;

export class Attachments {
  // root: [data-mw-attachments]. form: the comment's form. apiBase: the Site's
  // API origin for saved files. source: the comment's URL when editing, with
  // count saved attachments.
  constructor(root, { form, apiBase = '', source = '', count = 0 }) {
    this.root = root;
    this.form = form;
    this.apiBase = apiBase;
    this.input = root.querySelector('input[type=file]');
    this.gallery = root.querySelector('[data-mw-gallery]');
    this.files = [];
    this.saved = [];
    this.removed = [];
    this.urls = new Map();

    this.input.addEventListener('change', () => this.add([...this.input.files]));
    root.addEventListener('dragover', (event) => {
      event.preventDefault();
      root.classList.add('mw-dragover');
    });
    root.addEventListener('dragleave', () => root.classList.remove('mw-dragover'));
    root.addEventListener('drop', (event) => {
      event.preventDefault();
      root.classList.remove('mw-dragover');
      this.add([...event.dataTransfer.files]);
    });
    this.gallery.addEventListener('click', (event) => {
      const button = event.target.closest('[data-mw-remove]');
      if (button) this.remove(button.closest('li'));
    });

    if (count > 0 && source) this.loadSaved(source);
  }

  add(files) {
    for (const file of files) {
      if (!this.files.some((f) => sameFile(f, file))) this.files.push(file);
    }
    this.sync();
    this.render();
  }

  // The input submits exactly the listed files.
  sync() {
    const transfer = new DataTransfer();
    for (const file of this.files) transfer.items.add(file);
    this.input.files = transfer.files;
  }

  async loadSaved(source) {
    this.gallery.textContent = 'Loading attachments...';
    try {
      const response = await fetch(source + 'attachments/', { credentials: 'same-origin' });
      if (!response.ok) throw new Error(String(response.status));
      this.saved = (await response.json()).data?.attachments?.items || [];
    } catch {
      this.saved = [];
    }
    this.render();
  }

  remove(item) {
    if (!window.confirm('Are you sure you want to remove this attachment?')) return;
    if (item.dataset.hash) {
      this.removed.push(item.dataset.hash);
      this.saved = this.saved.filter((file) => file.fileHash !== item.dataset.hash);
      this.deleteField().value = this.removed.join(',');
    } else {
      const file = this.files[Number(item.dataset.index)];
      URL.revokeObjectURL(this.urls.get(file));
      this.urls.delete(file);
      this.files = this.files.filter((f) => f !== file);
      this.sync();
    }
    this.render();
  }

  deleteField() {
    let field = this.form.querySelector('input[name="attachments-delete"]');
    if (!field) {
      field = Object.assign(document.createElement('input'), { type: 'hidden', name: 'attachments-delete' });
      this.form.append(field);
    }
    return field;
  }

  clear() {
    for (const url of this.urls.values()) URL.revokeObjectURL(url);
    this.urls.clear();
    this.files = [];
    this.removed = [];
    this.form.querySelector('input[name="attachments-delete"]')?.remove();
    this.sync();
    this.render();
  }

  // Images first, as thumbnails, then other files by name.
  render() {
    const items = [
      ...this.saved.map((file) => ({
        name: file.fileName,
        image: IMAGE_EXTENSIONS.has(String(file.fileExt).toLowerCase()),
        src: () => this.apiBase + file.meta.links[0].href,
        data: { hash: file.fileHash },
      })),
      ...this.files.map((file, index) => ({
        name: file.name,
        image: file.type.startsWith('image/'),
        src: () => {
          if (!this.urls.has(file)) this.urls.set(file, URL.createObjectURL(file));
          return this.urls.get(file);
        },
        data: { index: String(index) },
      })),
    ].sort((a, b) => b.image - a.image);

    this.gallery.replaceChildren(...items.map((item) => {
      const li = document.createElement('li');
      li.className = item.image ? 'mw-attachment-image' : 'mw-attachment-file';
      Object.assign(li.dataset, item.data);
      if (item.image) {
        li.append(Object.assign(document.createElement('img'), { src: item.src(), alt: item.name }));
      } else {
        li.append(Object.assign(document.createElement('span'), { textContent: item.name }));
      }
      const remove = Object.assign(document.createElement('button'), { type: 'button', className: 'btn-close' });
      remove.dataset.mwRemove = '';
      remove.setAttribute('aria-label', 'Remove ' + item.name);
      li.append(remove);
      return li;
    }));
  }
}
