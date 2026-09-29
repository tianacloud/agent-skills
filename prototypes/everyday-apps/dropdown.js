function dropdown(name, label, value, options, id = name, compact = false) {
  const entries = options.map(option => Array.isArray(option) ? option : [option, option]);
  const text = entries.find(([key]) => key === value)?.[1] || '';
  return `<div class="dropdown ${compact ? 'compact' : ''}">
    <input type="hidden" name="${esc(name)}" id="${esc(id)}" value="${esc(value)}">
    <button type="button" class="dropdown-trigger" role="combobox" aria-label="${esc(label)}" aria-haspopup="listbox" aria-expanded="false" aria-controls="${esc(id)}-options">
      <span class="dropdown-value">${esc(text)}</span><span class="dropdown-chevron" aria-hidden="true"></span>
    </button>
    <div class="dropdown-menu" id="${esc(id)}-options" role="listbox" aria-label="${esc(label)}" popover="manual">
      ${entries.map(([key, text], index) => `<div class="dropdown-option" id="${esc(id)}-option-${index}" role="option" aria-selected="${key === value}" data-value="${esc(key)}"><span>${esc(text)}</span><span class="dropdown-check" aria-hidden="true">✓</span></div>`).join('')}
    </div>
  </div>`;
}

let openDropdown = null;
let activeOption = 0;
function closeDropdown() {
  if (!openDropdown) return;
  const trigger = openDropdown.querySelector('.dropdown-trigger');
  openDropdown.querySelector('.dropdown-menu').hidePopover();
  trigger.setAttribute('aria-expanded', 'false');
  trigger.removeAttribute('aria-activedescendant');
  openDropdown = null;
}
function positionDropdown() {
  if (!openDropdown) return;
  const rect = openDropdown.querySelector('.dropdown-trigger').getBoundingClientRect();
  const menu = openDropdown.querySelector('.dropdown-menu');
  const width = Math.min(Math.max(rect.width, 150), innerWidth - 24);
  const below = innerHeight - rect.bottom - 14;
  const above = rect.top - 14;
  const height = Math.min(menu.scrollHeight, 260);
  const upward = below < height && above > below;
  menu.style.width = `${width}px`;
  menu.style.maxHeight = `${Math.max(48, Math.min(260, upward ? above : below))}px`;
  menu.style.left = `${Math.max(12, Math.min(rect.left, innerWidth - width - 12))}px`;
  menu.style.top = `${upward ? rect.top - Math.min(height, above) - 6 : rect.bottom + 6}px`;
}
function highlightOption(index) {
  const options = [...openDropdown.querySelectorAll('[role=option]')];
  activeOption = Math.max(0, Math.min(index, options.length - 1));
  options.forEach((option, i) => option.classList.toggle('active', i === activeOption));
  openDropdown.querySelector('.dropdown-trigger').setAttribute('aria-activedescendant', options[activeOption].id);
  options[activeOption].scrollIntoView({block:'nearest'});
}
function showDropdown(root) {
  closeDropdown();
  openDropdown = root;
  const menu = root.querySelector('.dropdown-menu');
  root.querySelector('.dropdown-trigger').setAttribute('aria-expanded', 'true');
  menu.showPopover();
  positionDropdown();
  highlightOption([...menu.children].findIndex(option => option.getAttribute('aria-selected') === 'true'));
}
function chooseOption(option) {
  const root = openDropdown;
  const input = root.querySelector('input');
  input.value = option.dataset.value;
  root.querySelector('.dropdown-value').textContent = option.firstElementChild.textContent;
  root.querySelectorAll('[role=option]').forEach(item => item.setAttribute('aria-selected', String(item === option)));
  closeDropdown();
  root.querySelector('.dropdown-trigger').focus();
  input.dispatchEvent(new Event('input', {bubbles:true}));
  input.dispatchEvent(new Event('change', {bubbles:true}));
}
document.addEventListener('click', event => {
  const trigger = event.target.closest('.dropdown-trigger');
  if (trigger) {
    const root = trigger.closest('.dropdown');
    if (openDropdown === root) closeDropdown(); else showDropdown(root);
    return;
  }
  const option = event.target.closest('.dropdown-option');
  if (option && openDropdown?.contains(option)) chooseOption(option);
});
document.addEventListener('pointerdown', event => {
  if (openDropdown && !openDropdown.contains(event.target)) closeDropdown();
});
document.addEventListener('keydown', event => {
  const trigger = event.target.closest('.dropdown-trigger');
  if (!trigger) return;
  const root = trigger.closest('.dropdown');
  if (event.key === 'Tab') { closeDropdown(); return; }
  if (event.key === 'Escape' && openDropdown) {
    event.preventDefault();
    event.stopImmediatePropagation();
    closeDropdown();
    return;
  }
  if (!['ArrowDown','ArrowUp','Home','End','Enter',' '].includes(event.key)) return;
  event.preventDefault();
  if (openDropdown !== root) {
    showDropdown(root);
    if (event.key === 'Home') highlightOption(0);
    if (event.key === 'End') highlightOption(root.querySelectorAll('[role=option]').length - 1);
    return;
  }
  if (event.key === 'Enter' || event.key === ' ') {
    chooseOption(root.querySelectorAll('[role=option]')[activeOption]);
  } else {
    highlightOption(event.key === 'Home' ? 0 : event.key === 'End' ? root.querySelectorAll('[role=option]').length - 1 : activeOption + (event.key === 'ArrowDown' ? 1 : -1));
  }
}, true);
window.addEventListener('resize', positionDropdown);
document.addEventListener('scroll', event => {
  if (openDropdown && event.target !== openDropdown.querySelector('.dropdown-menu')) positionDropdown();
}, true);
document.addEventListener('close', event => {
  if (openDropdown && event.target.contains(openDropdown)) closeDropdown();
}, true);
