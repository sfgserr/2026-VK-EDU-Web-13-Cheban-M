import json
from smtplib import SMTPException
from urllib.request import Request, urlopen

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from questions.models import Answer


def question_channel(question_id):
    return f'questions:{question_id}'


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def publish_answer(question_id, answer_id, answer_url):
    payload = {
        'channel': question_channel(question_id),
        'data': {
            'answer_id': str(answer_id),
            'answer_url': answer_url,
            'card_url': reverse('answer_card', args=[question_id, answer_id]),
        },
    }
    request = Request(
        f'{settings.CENTRIFUGO_API_URL}/publish',
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json', 'X-API-Key': settings.CENTRIFUGO_API_KEY},
    )
    with urlopen(request, timeout=5) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(f"Centrifugo: {result['error']}")


@shared_task(autoretry_for=(OSError, SMTPException), retry_backoff=True, max_retries=3)
def email_question_author(answer_id, answer_url):
    answer = Answer.objects.filter(pk=answer_id).select_related('question__author').first()
    if answer is None or not answer.question.author.email:
        return
    send_mail(
        'Новый ответ на ваш вопрос в Forum',
        f'На вопрос «{answer.question.title}» опубликован новый ответ.\n\n'
        f'{settings.PUBLIC_SITE_URL}{answer_url}',
        settings.DEFAULT_FROM_EMAIL,
        [answer.question.author.email],
    )
