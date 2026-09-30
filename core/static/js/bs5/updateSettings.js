// Notification settings (BS5-09): forms/update_settings.html, marked
// data-mw-settings. Ported from the page's inline FormCheckboxTable script
// without jQuery. The global switch (data-mw-master) turns every switch in its
// data-mw-group on or off with it, and while it is off the others are
// disabled, as today. Cancel (the form's reset) enables them all again, as
// the page loaded them.

export function setGroup(form, group, on) {
  for (const box of form.querySelectorAll(`input[type=checkbox][data-mw-group="${group}"]`)) {
    box.checked = on;
    if (!box.hasAttribute('data-mw-master')) box.disabled = !on;
  }
}

for (const form of document.querySelectorAll('form[data-mw-settings]')) {
  form.addEventListener('change', (event) => {
    const box = event.target;
    if (box.matches('[data-mw-master]')) setGroup(form, box.dataset.mwGroup, box.checked);
  });
  form.addEventListener('reset', () => {
    for (const box of form.querySelectorAll('input[data-mw-group]')) box.disabled = false;
  });
}
