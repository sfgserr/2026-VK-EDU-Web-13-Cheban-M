(() => {
  const list = document.getElementById('answer-list');
  const notice = document.getElementById('new-answer-notice');
  const centrifuge = new Centrifuge(list.dataset.websocketUrl, {
    getToken: async () => {
      const response = await fetch(list.dataset.tokenUrl);
      if (!response.ok) throw new Error('Не удалось подключить обновление ответов.');
      return (await response.json()).token;
    },
  });
  const subscription = centrifuge.newSubscription(list.dataset.channel);

  function showNotice(url) {
    notice.querySelector('a').href = url;
    notice.hidden = false;
  }

  subscription.on('publication', async ({ data }) => {
    const cardId = `answer-${data.answer_id}`;
    if (document.getElementById(cardId)) return;
    if (list.dataset.page !== '1') {
      showNotice(data.answer_url);
      return;
    }

    try {
      const response = await fetch(data.card_url);
      if (!response.ok) throw new Error('Не удалось загрузить ответ.');
      const card = await response.text();
      if (document.getElementById(cardId)) return;
      document.getElementById('no-answers')?.remove();
      list.insertAdjacentHTML('afterbegin', card);
    } catch {
      showNotice(data.answer_url);
    }
  });

  subscription.subscribe();
  centrifuge.connect();
})();
