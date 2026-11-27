(() => {
  const form = document.querySelector('[data-suggestions-url]');
  const input = form.elements.q;
  const results = form.querySelector('[data-search-results]');
  let timer;
  let pending;

  function close() {
    clearTimeout(timer);
    pending?.abort();
    results.hidden = true;
  }

  input.addEventListener('input', () => {
    close();
    const query = input.value.trim();
    if (query.length < 2) return;

    timer = setTimeout(async () => {
      const controller = new AbortController();
      pending = controller;
      const url = new URL(form.dataset.suggestionsUrl, window.location.origin);
      url.searchParams.set('q', query);
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) return;
        const { results: matches } = await response.json();
        if (controller.signal.aborted) return;

        results.replaceChildren(...matches.map(({ title, url }) => {
          const link = document.createElement('a');
          link.className = 'list-group-item list-group-item-action text-break';
          link.href = url;
          link.textContent = title;
          return link;
        }));
        results.hidden = matches.length === 0;
      } catch {
        if (!controller.signal.aborted) results.hidden = true;
      }
    }, 300);
  });

  form.addEventListener('focusout', (event) => {
    if (!form.contains(event.relatedTarget)) close();
  });
  form.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      input.focus();
      close();
    }
    if (event.key === 'ArrowDown' && event.target === input && !results.hidden) {
      event.preventDefault();
      results.querySelector('a')?.focus();
    }
  });
})();
