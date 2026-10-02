// The membership group form (BS5-14): forms/memberships.html, marked
// data-mw-membership-form. Ported from js/membership_form.js and the form's
// inline script without jQuery:
// - the Yes/No answers keep each other consistent, as before: a moderator
//   can do everything, a banned group nothing, and guests cannot post;
// - Criteria, the rules people join the group by, with the comparisons each
//   kind of value allows;
// - the individuals are the people widget's (peopleWidget.js);
// - Save and Delete post JSON to microcosms/views.py members_api, as before,
//   then go back to the list of groups.

import './peopleWidget.js';

const PREDICATES = {
  gt: 'is greater than',
  ge: 'is greater than or equal to',
  eq: 'equals',
  le: 'is less than or equal to',
  lt: 'is less than',
  neq: 'is not equal to',
  substr: 'contains',
  nsubstr: 'does not contain',
};

// The comparisons each kind of value allows; the first is chosen for it.
const ALLOWED = {
  all: Object.keys(PREDICATES),
  number: ['gt', 'ge', 'eq', 'le', 'lt', 'neq'],
  date: ['le', 'gt', 'ge', 'eq', 'lt', 'neq'],
  bool: ['eq', 'neq'],
  string: ['eq', 'neq', 'substr', 'nsubstr'],
};

// The profile columns a criterion may name; anything else is a custom attribute.
const COLUMNS = {
  email: { kind: 'string', type: 'text', placeholder: '@example.com' },
  commentCount: { kind: 'number', type: 'number', placeholder: '1000' },
  created: { kind: 'date', type: 'date', placeholder: '2014-02-14' },
  profileName: { kind: 'string', type: 'text', placeholder: 'John Smith' },
};

const ISO_DATE = /^\d{4}-\d\d-\d\d$/;

function isIsoDate(value) {
  if (!ISO_DATE.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCMonth() === m - 1 && date.getUTCDate() === d;
}

// What kind of value a custom attribute's value is, as js/membership_form.js read it.
function sniffDatatype(value) {
  if (value === '') return 'all';
  if (value === 'true' || value === 'false') return 'bool';
  if (!Number.isNaN(Number(value))) return 'number';
  if (isIsoDate(value)) return 'date';
  return 'string';
}

// A criterion as members_api sends it to the API. Criteria joined by "or"
// start a new group; "and" joins the group before.
function criteriaForApi(rows) {
  let orGroup = 0;
  return rows.map(({ andor, key, predicate, value }) => {
    if (andor === 'or') orGroup++;
    const criterion = { orGroup };
    if (key in COLUMNS) criterion.profileColumn = key;
    else criterion.attrKey = key;
    criterion.predicate = predicate;
    const kind = sniffDatatype(value);
    if (kind === 'all') throw new Error('One of the criteria has a blank value');
    criterion.value = kind === 'number' ? Number(value) : kind === 'bool' ? value === 'true' : value;
    return criterion;
  });
}

// ---------------------------------------------------------------------------
// The Yes/No answers

const RESTRICTED = ['can_create', 'can_edit_others', 'can_delete_others', 'can_close_own', 'can_open_own'];

// What each answer forces on the others: { name: { answer: { other: its answer } } }.
const RULES = {
  include_unregistered: { 1: { is_moderator: 0, ...each(RESTRICTED, 0) } },
  is_moderator: { 1: { include_unregistered: 0, is_banned: 0, can_read: 1, ...each(RESTRICTED, 1) } },
  is_banned: { 1: { is_moderator: 0, can_read: 0, ...each(RESTRICTED, 0) } },
  can_read: { 1: { is_banned: 0 }, 0: { is_moderator: 0, ...each(RESTRICTED, 0) } },
};
for (const name of RESTRICTED) {
  RULES[name] = { 1: { include_unregistered: 0, is_banned: 0, can_read: 1 }, 0: { is_moderator: 0 } };
}

function each(names, value) {
  return Object.fromEntries(names.map((name) => [name, value]));
}

function answer(form, name) {
  return form.querySelector(`input[name="${name}"]:checked`)?.value === '1';
}

function setAnswer(form, name, value) {
  const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
  if (input) input.checked = true;
}

// ---------------------------------------------------------------------------
// Criteria

class Criteria {
  constructor(root) {
    this.root = root;
    this.empty = root.querySelector('[data-mw-criteria-empty]');
    this.listPart = root.querySelector('[data-mw-criteria-list]');
    this.items = root.querySelector('[data-mw-criteria-items]');
    this.form = root.querySelector('[data-mw-criteria-form]');
    this.condition = this.form.querySelector('select[name=condition]');
    this.predicate = this.form.querySelector('select[name=predicate]');
    this.value = this.form.querySelector('input[name=value]');
    this.feedback = this.value.nextElementSibling;
    this.rows = [...this.items.children].map((li) => ({ ...li.dataset }));
    this.lastCondition = this.condition.value;

    root.addEventListener('click', (event) => {
      if (event.target.closest('[data-mw-criteria-toggle]')) this.toggleForm();
      const remove = event.target.closest('[data-mw-criteria-remove]');
      if (remove) this.remove(Number(remove.dataset.mwCriteriaRemove));
      if (event.target.closest('[data-mw-criteria-add]')) this.add();
    });
    this.condition.addEventListener('change', () => this.onCondition());
    this.value.addEventListener('input', () => {
      this.clearError();
      if (!(this.condition.value in COLUMNS)) this.restrict(sniffDatatype(this.value.value.trim()));
    });
    // Enter adds the criterion rather than sending the group.
    this.value.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        this.add();
      }
    });
    this.applyColumn(this.condition.value);
    this.render();
  }

  toggleForm() {
    this.form.hidden = !this.form.hidden;
    if (!this.form.hidden) this.condition.focus();
  }

  // A custom attribute asks for its name, as before; cancelling keeps the last choice.
  onCondition() {
    if (this.condition.value === '') {
      const key = window.prompt('Please enter the profile attribute name', 'is_member')?.trim();
      if (!key) {
        this.condition.value = this.lastCondition;
        return;
      }
      let option = [...this.condition.options].find((o) => o.value === key);
      if (!option) {
        option = new Option(key, key);
        this.condition.add(option, this.condition.querySelector('option[value=""]'));
      }
      this.condition.value = key;
    }
    this.lastCondition = this.condition.value;
    this.applyColumn(this.condition.value);
  }

  applyColumn(key) {
    const column = COLUMNS[key] || { kind: 'all', type: 'text', placeholder: 'Value' };
    this.value.type = column.type;
    this.value.placeholder = column.placeholder;
    this.value.step = column.type === 'number' ? '1' : '';
    this.value.value = '';
    this.clearError();
    this.restrict(column.kind, true);
  }

  restrict(kind, force = false) {
    if (!force && this.predicate.dataset.kind === kind) return;
    this.predicate.dataset.kind = kind;
    const allowed = ALLOWED[kind];
    for (const option of this.predicate.options) option.disabled = !allowed.includes(option.value);
    this.predicate.value = allowed[0];
  }

  clearError() {
    this.value.classList.remove('is-invalid');
  }

  error(message) {
    this.feedback.textContent = message;
    this.value.classList.add('is-invalid');
    this.value.focus();
  }

  add() {
    const value = this.value.value.trim();
    if (!value || !this.value.validity.valid) {
      this.error(this.condition.value === 'created' && !this.value.validity.valid
        ? 'A date value in ISO format 2014-02-14 must be specified.'
        : 'A value must be specified.');
      return;
    }
    if (this.condition.value === 'created' && !isIsoDate(value)) {
      this.error('A date value in ISO format 2014-02-14 must be specified.');
      return;
    }
    this.rows.push({
      andor: this.form.querySelector('input[name=switch]:checked').value,
      key: this.condition.value,
      predicate: this.predicate.value,
      // Whole numbers only, as before.
      value: this.value.type === 'number' ? String(parseInt(value, 10)) : value,
    });
    this.value.value = '';
    this.render();
  }

  remove(index) {
    this.rows.splice(index, 1);
    this.render();
  }

  render() {
    const items = [];
    this.rows.forEach((row, index) => {
      if (index > 0 && row.andor === 'or') {
        const or = document.createElement('li');
        or.innerHTML = '<em>or</em>';
        items.push(or);
      }
      const li = document.createElement('li');
      li.className = 'mw-criterion';
      const key = document.createElement('strong');
      key.textContent = row.key;
      const value = document.createElement('strong');
      value.textContent = row.value;
      const remove = document.createElement('button');
      Object.assign(remove, { type: 'button', className: 'btn btn-link btn-sm p-0 mw-criterion-remove', textContent: 'Remove' });
      remove.dataset.mwCriteriaRemove = String(index);
      remove.setAttribute('aria-label', `Remove ${row.key} ${PREDICATES[row.predicate] || row.predicate} ${row.value}`);
      li.append(index > 0 && row.andor === 'and' ? 'and ' : '', key, ` ${PREDICATES[row.predicate] || row.predicate} `, value, ' ', remove);
      items.push(li);
    });
    this.items.replaceChildren(...items);
    this.empty.hidden = this.rows.length > 0;
    this.listPart.hidden = this.rows.length === 0;
  }
}

// ---------------------------------------------------------------------------
// The form

class MembershipForm {
  constructor(form) {
    this.form = form;
    this.roleId = Number(form.dataset.roleId) || 0;
    this.criteria = new Criteria(form.querySelector('[data-mw-criteria]'));
    this.name = form.querySelector('input[name=name]');
    this.ids = form.querySelector('[data-mw-people-ids]');
    this.errorBox = form.querySelector('[data-mw-membership-error]');

    form.addEventListener('change', (event) => {
      const rules = RULES[event.target.name]?.[event.target.value];
      for (const [name, value] of Object.entries(rules || {})) setAnswer(form, name, value);
    });
    form.addEventListener('input', (event) => {
      if (event.target === this.name) this.name.classList.remove('is-invalid');
    });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      this.save();
    });
    document.querySelector('[data-mw-delete-role]')?.addEventListener('click', () => this.deleteRole());
    form.dataset.mwReady = '';
  }

  role() {
    const yes = (name) => answer(this.form, name);
    return {
      id: this.roleId,
      title: this.name.value.trim(),
      includeGuests: yes('include_unregistered'),
      includeUsers: yes('include_registered'),
      moderator: yes('is_moderator'),
      banned: yes('is_banned'),
      read: yes('can_read'),
      create: yes('can_create'),
      update: yes('can_edit_others'),
      delete: yes('can_delete_others'),
      closeOwn: yes('can_close_own'),
      openOwn: yes('can_open_own'),
      readOthers: yes('can_read'),
    };
  }

  save() {
    this.showError('');
    const role = this.role();
    if (!role.title) {
      this.name.classList.add('is-invalid');
      this.name.focus();
      return;
    }
    let criteria;
    try {
      criteria = criteriaForApi(this.criteria.rows);
    } catch (error) {
      this.showError(error.message + '.');
      return;
    }
    const profiles = this.ids.value.split(',').filter(Boolean);
    this.send({ role, profiles, criteria }, 'The membership group could not be saved. Please try again.');
  }

  deleteRole() {
    if (!window.confirm('Deleting a membership group will change permissions for all members of this groups.\n\nContinue with deletion?')) return;
    this.send({ deleteRole: this.roleId }, 'The membership group could not be deleted. Please try again.');
  }

  async send(data, failure) {
    const fields = [...this.form.elements].filter((field) => !field.disabled);
    for (const field of fields) field.disabled = true;
    try {
      const response = await fetch(this.form.action, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json; charset=UTF-8',
          'X-CSRFToken': this.form.querySelector('input[name=csrfmiddlewaretoken]').value,
        },
        body: JSON.stringify(data),
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(String(response.status));
      window.location.assign(this.form.dataset.doneUrl);
    } catch {
      // Let people fix things and try again.
      for (const field of fields) field.disabled = false;
      this.showError(failure);
    }
  }

  showError(message) {
    this.errorBox.textContent = message;
    this.errorBox.hidden = !message;
  }
}

for (const form of document.querySelectorAll('[data-mw-membership-form]')) {
  new MembershipForm(form);
}
