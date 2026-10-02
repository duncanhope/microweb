// The people widget (BS5-13): choose members by name. Ported from
// js/peopleWidget.js (PeopleWidget and Participating) without jQuery, and
// shared by the event form's invites (BS5-12), the New message form and the
// Share this message modal on a huddle.
//
// Markup, inside an element marked data-mw-people:
// - a text input: a combobox of the members whose names start with what is
//   typed, searched through mentions.js's ProfileSearch (one search at a
//   time, only the latest may answer);
// - ul.mw-people-chosen: the people chosen, as chips with a remove button;
// - input[data-mw-people-ids]: their profile ids, joined by
//   data-mw-separator (a comma unless the element says otherwise);
// - input[data-mw-people-json], optional: the same people as JSON, so a form
//   sent back with an error shows them again.
// data-mw-invited holds the people chosen already, as JSON
// [{ id, profileName, avatar, sticky }]; sticky people have no remove button.
// data-mw-members holds people the search leaves out, because they are in
// already (a huddle's participants).
// A [data-mw-people-submit] button in the same form is enabled only while
// someone is chosen.
//
// Importing this module wires every [data-mw-people] on the page.

import { API_BASE, ProfileSearch } from './mentions.js';

const DEBOUNCE_MS = 150;

function readPeople(json) {
  try {
    const people = JSON.parse(json || '[]');
    return Array.isArray(people) ? people.filter((person) => person && person.id) : [];
  } catch {
    return [];
  }
}

let count = 0;

export class PeopleWidget {
  constructor(root, { apiBase = '' } = {}) {
    root.mwPeople = this;
    this.apiBase = apiBase;
    this.searches = new ProfileSearch(apiBase);
    this.input = root.querySelector('input[type=text]');
    this.chosen = root.querySelector('.mw-people-chosen');
    this.ids = root.querySelector('[data-mw-people-ids]');
    this.json = root.querySelector('[data-mw-people-json]');
    this.separator = root.dataset.mwSeparator || ',';
    this.submit = root.closest('form')?.querySelector('[data-mw-people-submit]');
    this.people = readPeople(root.dataset.mwInvited);
    this.members = new Set(readPeople(root.dataset.mwMembers).map((person) => person.id));
    this.results = [];
    this.active = -1;

    const id = (this.input.id || 'mw-people-' + ++count) + '-results';
    this.list = document.createElement('ul');
    Object.assign(this.list, { id, className: 'dropdown-menu mw-mentions mw-people-results' });
    this.list.setAttribute('role', 'listbox');
    this.list.setAttribute('aria-label', 'Members');
    this.status = document.createElement('div');
    this.status.className = 'visually-hidden';
    this.status.setAttribute('role', 'status');
    // After the input group, so the input keeps its rounded corners.
    this.input.parentElement.after(this.list, this.status);
    this.input.setAttribute('role', 'combobox');
    this.input.setAttribute('aria-autocomplete', 'list');
    this.input.setAttribute('aria-expanded', 'false');
    this.input.setAttribute('aria-controls', id);

    this.input.addEventListener('input', () => {
      clearTimeout(this.timer);
      this.timer = setTimeout(() => this.search(), DEBOUNCE_MS);
    });
    this.input.addEventListener('keydown', (event) => this.onKeydown(event));
    this.input.addEventListener('blur', () => this.close());
    // Keep focus in the box while the pointer picks a member.
    this.list.addEventListener('mousedown', (event) => event.preventDefault());
    this.list.addEventListener('click', (event) => {
      const option = event.target.closest('[role=option]');
      if (option) this.add(Number(option.dataset.index));
    });
    this.chosen.addEventListener('click', (event) => {
      const button = event.target.closest('[data-mw-remove]');
      if (button) this.remove(Number(button.dataset.mwRemove));
    });
    this.render();
  }

  get isOpen() {
    return this.list.classList.contains('show');
  }

  async search() {
    const term = this.input.value.trim();
    if (!term) {
      this.close();
      return;
    }
    let found;
    try {
      found = await this.searches.search(term);
    } catch {
      this.hide();
      return;
    }
    if (!found) return;
    const taken = new Set([...this.members, ...this.people.map((person) => person.id)]);
    this.results = found.filter((profile) => !taken.has(profile.id));
    this.open(term);
  }

  avatar(person) {
    const img = document.createElement('img');
    img.alt = '';
    img.width = img.height = 20;
    img.src = new URL(person.avatar || '/static/img/avatar.gif', this.apiBase || location.href).href;
    return img;
  }

  open(term) {
    if (!this.results.length) {
      const empty = document.createElement('li');
      empty.className = 'dropdown-item-text';
      empty.textContent = 'No results';
      this.list.replaceChildren(empty);
      this.status.textContent = `No members found for ${term}`;
    } else {
      this.list.replaceChildren(...this.results.map((profile, index) => {
        const option = document.createElement('li');
        option.id = `${this.list.id}-${index}`;
        option.className = 'dropdown-item';
        option.dataset.index = String(index);
        option.setAttribute('role', 'option');
        option.append(this.avatar(profile), document.createTextNode(profile.profileName));
        return option;
      }));
      this.status.textContent = `${this.results.length} member${this.results.length === 1 ? '' : 's'} found, use up and down to choose`;
    }
    this.list.classList.add('show');
    this.input.setAttribute('aria-expanded', 'true');
    this.setActive(this.results.length ? 0 : -1);
  }

  // Stop any search, and hide the list.
  close() {
    clearTimeout(this.timer);
    this.searches.cancel();
    this.hide();
  }

  // Hide the list only: a search typed since may still be on its way.
  hide() {
    this.list.classList.remove('show');
    this.list.replaceChildren();
    this.input.setAttribute('aria-expanded', 'false');
    this.input.removeAttribute('aria-activedescendant');
    this.results = [];
    this.active = -1;
  }

  setActive(index) {
    const options = [...this.list.querySelectorAll('[role=option]')];
    if (!options.length) {
      this.active = -1;
      return;
    }
    this.active = (index + options.length) % options.length;
    for (const [i, option] of options.entries()) {
      option.classList.toggle('active', i === this.active);
      option.setAttribute('aria-selected', String(i === this.active));
    }
    this.input.setAttribute('aria-activedescendant', options[this.active].id);
  }

  onKeydown(event) {
    if (event.isComposing) return;
    // Enter never sends the form from here: it picks a member or does nothing.
    if (event.key === 'Enter') event.preventDefault();
    if (!this.isOpen) return;
    switch (event.key) {
      case 'ArrowDown':
        this.setActive(this.active + 1);
        break;
      case 'ArrowUp':
        this.setActive(this.active - 1);
        break;
      case 'Enter':
        if (this.active > -1) this.add(this.active);
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

  add(index) {
    const profile = this.results[index];
    if (!profile) return;
    this.people.push({ id: profile.id, profileName: profile.profileName, avatar: profile.avatar || '' });
    this.input.value = '';
    this.close();
    this.render();
    this.status.textContent = `${profile.profileName} added`;
  }

  remove(id) {
    const person = this.people.find((p) => p.id === id);
    if (!person || person.sticky) return;
    this.people = this.people.filter((p) => p !== person);
    this.render();
    this.status.textContent = `${person.profileName} removed`;
    this.input.focus();
  }

  render() {
    this.chosen.replaceChildren(...this.people.map((person) => {
      const item = document.createElement('li');
      item.className = 'mw-people-chip';
      item.append(this.avatar(person), document.createTextNode(person.profileName));
      if (!person.sticky) {
        const button = document.createElement('button');
        Object.assign(button, { type: 'button', className: 'btn-close' });
        button.dataset.mwRemove = String(person.id);
        button.setAttribute('aria-label', `Remove ${person.profileName}`);
        item.append(button);
      }
      return item;
    }));
    this.chosen.hidden = !this.people.length;
    this.ids.value = this.people.map((person) => person.id).join(this.separator);
    if (this.json) this.json.value = this.people.length ? JSON.stringify(this.people) : '';
    if (this.submit) this.submit.disabled = !this.people.length;
  }
}

for (const root of document.querySelectorAll('[data-mw-people]')) {
  if (!root.mwPeople) new PeopleWidget(root, { apiBase: API_BASE });
}
