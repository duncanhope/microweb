// The Color mode toggle (BS5-06), core/templates_bs5/base_color_mode.html.
// Choosing Light, Dark or Auto applies it at once, without a reload, and
// keeps it in the color_mode cookie so the server renders the next page in
// it. The inline script in base.html's <head> turns the choice into
// data-bs-theme (window.mwApplyColorMode) and makes Auto follow the system.

const COOKIE = 'color_mode';
const ONE_YEAR = 60 * 60 * 24 * 365;

function chooseColorMode(mode) {
  document.documentElement.dataset.mwColorMode = mode;
  window.mwApplyColorMode();
  const secure = location.protocol === 'https:' ? '; secure' : '';
  document.cookie = `${COOKIE}=${mode}; max-age=${ONE_YEAR}; path=/; samesite=lax${secure}`;
}

function showChoice(toggle, choice) {
  for (const item of toggle.parentElement.querySelectorAll('[data-mw-color-mode-value]')) {
    const chosen = item === choice;
    item.classList.toggle('active', chosen);
    item.setAttribute('aria-pressed', String(chosen));
  }
  const name = choice.textContent.trim();
  toggle.querySelector('.mw-color-mode-current').replaceChildren(choice.querySelector('.bi').cloneNode(true));
  toggle.querySelector('.mw-color-mode-text').textContent = name;
  toggle.setAttribute('aria-label', `Colour mode (${name})`);
}

document.addEventListener('click', (event) => {
  const choice = event.target.closest('[data-mw-color-mode-value]');
  if (!choice) return;
  const toggle = choice.closest('.dropdown').querySelector('[data-bs-toggle="dropdown"]');
  chooseColorMode(choice.dataset.mwColorModeValue);
  showChoice(toggle, choice);
  toggle.focus();
});
