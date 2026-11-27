async function submitAction(form, fields) {
  const data = new FormData(form);
  for (const [name, value] of Object.entries(fields)) {
    data.set(name, value);
  }

  const response = await fetch(form.action, {
    method: 'POST',
    body: data,
    headers: { Accept: 'application/json' },
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.error || 'Не удалось выполнить действие.');
    error.result = result;
    throw error;
  }
  return result;
}

function showVote(form, result) {
  form.querySelector('[data-rating]').textContent = result.rating;
  for (const button of form.querySelectorAll('button[name="value"]')) {
    const active = Number(button.value) === result.vote;
    button.classList.toggle('btn-outline-secondary', !active);
    button.classList.toggle(button.value === '1' ? 'btn-success' : 'btn-danger', active);
    button.setAttribute('aria-pressed', String(active));
  }
}

document.addEventListener('submit', async (event) => {
  const form = event.target;
  if (form.matches('form[data-ajax="correct"]')) {
    event.preventDefault();
    return;
  }
  if (!form.matches('form[data-ajax="vote"]')) return;

  event.preventDefault();
  const button = event.submitter;
  if (!button || button.disabled) return;

  const buttons = form.querySelectorAll('button[name="value"]');
  buttons.forEach((item) => { item.disabled = true; });
  try {
    showVote(form, await submitAction(form, { value: button.value }));
  } catch (error) {
    if (error.result?.duplicate) showVote(form, error.result);
    alert(error.message);
  } finally {
    buttons.forEach((item) => {
      item.disabled = item.getAttribute('aria-pressed') === 'true';
    });
  }
});

let savingCorrectAnswer = false;
document.addEventListener('change', async (event) => {
  const checkbox = event.target;
  const form = checkbox.closest('form[data-ajax="correct"]');
  if (!form || checkbox.type !== 'checkbox') return;

  const checked = checkbox.checked;
  if (savingCorrectAnswer) {
    checkbox.checked = !checked;
    return;
  }
  const checkboxes = document.querySelectorAll('form[data-ajax="correct"] input[type="checkbox"]');
  savingCorrectAnswer = true;
  checkboxes.forEach((item) => { item.disabled = true; });
  try {
    const result = await submitAction(form, { correct: checked ? '1' : '0' });
    checkboxes.forEach((item) => {
      if (item === checkbox) item.checked = result.correct;
      else if (result.correct) item.checked = false;
      item.closest('.card').classList.toggle('border-success', item.checked);
    });
  } catch (error) {
    checkbox.checked = !checked;
    alert(error.message);
  } finally {
    checkboxes.forEach((item) => { item.disabled = false; });
    savingCorrectAnswer = false;
  }
});
