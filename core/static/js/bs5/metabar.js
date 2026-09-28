// The metabar's Follow control, imported by base.js on pages that have one.
// Ported from js/metabar.js without jQuery. The metabar drawer that file also
// drove is now a Bootstrap offcanvas and needs no script.
//
// A family template renders the control with data attributes in place of the
// inline `new Subscribe({...})` call:
//
//   <div data-mw-subscribe data-url="{% url 'single-watcher' %}" data-item-type="conversation"
//        data-item-id="123" data-update-type="1" data-subscribed="true|false">
//     {% csrf_token %}
//     <button type="button" data-mw-subscribe-toggle>Follow</button>
//     <input type="checkbox" name="emailme">
//   </div>
//
// The root gets data-state="on", "off" or "loading", and the class "active"
// while followed, for the template's CSS.

class Subscribe {
  constructor(root) {
    this.root = root;
    const { url, itemType, itemId, updateType, subscribed } = root.dataset;
    this.url = url;
    this.subscribed = subscribed === 'true';
    this.fields = {
      updateTypeId: updateType || '1',
      itemId,
      itemType,
      csrfmiddlewaretoken: root.querySelector('input[name=csrfmiddlewaretoken]')?.value || '',
    };
    root.addEventListener('click', (event) => {
      if (event.target.closest('[data-mw-subscribe-toggle]')) {
        event.preventDefault();
        this.toggle();
      }
    });
    root.addEventListener('change', (event) => {
      if (event.target.name === 'emailme') this.setEmail(event.target.checked);
    });
    // The control lives in forms that must never submit.
    root.addEventListener('submit', (event) => event.preventDefault());
    this.render();
  }

  post(extra) {
    return fetch(this.url, {
      method: 'POST',
      body: new URLSearchParams({ ...this.fields, ...extra }),
      credentials: 'same-origin',
    }).then((response) => {
      if (!response.ok) throw new Error('Watcher update failed: ' + response.status);
      return response;
    });
  }

  toggle() {
    if (this.root.dataset.state === 'loading') return;
    this.root.dataset.state = 'loading';
    this.root.classList.remove('active');
    this.post(this.subscribed ? { delete: 'true' } : {})
      .then(() => { this.subscribed = !this.subscribed; })
      .catch(() => {})
      .finally(() => this.render());
  }

  setEmail(on) {
    this.post({ emailMe: String(on), patch: 'true' }).catch(() => {});
  }

  render() {
    this.root.dataset.state = this.subscribed ? 'on' : 'off';
    this.root.classList.toggle('active', this.subscribed);
  }
}

for (const root of document.querySelectorAll('[data-mw-subscribe]')) {
  new Subscribe(root);
}
