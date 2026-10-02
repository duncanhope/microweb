// The check before a form is sent (BS5-08, split out of simpleEditor.js in
// BS5-14 so a form without a comment box loads only this): the Constraint
// Validation API and Bootstrap's .is-invalid, in place of formValidator.js.
// Importing this module wires every form marked data-mw-validate.

const wired = new WeakSet();

// Required fields must hold more than spaces; the first invalid field gets focus.
export function validateOnSubmit(form) {
  if (wired.has(form)) return;
  wired.add(form);
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

for (const form of document.querySelectorAll('form[data-mw-validate]')) validateOnSubmit(form);
