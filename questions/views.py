import logging
import time

import jwt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.csrf import csrf_failure as default_csrf_failure
from kombu.exceptions import OperationalError

from core.utils import paginate
from questions.forms import AnswerForm, CorrectAnswerForm, QuestionForm, VoteForm
from questions.models import Answer, Question, Tag
from questions.tasks import email_question_author, publish_answer, question_channel

ANSWERS_PER_PAGE = 10
logger = logging.getLogger(__name__)


def search_text(request):
    return request.GET.get('q', '').replace('\x00', '').strip()[:100]


def index(request):
    query = search_text(request)
    items = Question.objects.search(query).for_display() if query else Question.objects.newest()
    page = paginate(items.with_vote(request.user), request)
    return render(request, 'questions/index.html', {'page': page, 'query': query})


@require_GET
def search_suggestions(request):
    query = search_text(request)
    items = Question.objects.search(query).only('title')[:8] if len(query) >= 2 else []
    return JsonResponse({'results': [
        {'title': item.title, 'url': item.get_absolute_url()} for item in items
    ]})


def hot(request):
    page = paginate(Question.objects.best().with_vote(request.user), request)
    return render(request, 'questions/hot.html', {'page': page})


def tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    page = paginate(Question.objects.by_tag(tag).with_vote(request.user), request)
    return render(request, 'questions/tag.html', {'page': page, 'tag_name': tag.name})


def enqueue_answer_jobs(answer, url):
    if settings.CENTRIFUGO_API_KEY:
        enqueue(publish_answer, answer.question_id, answer.pk, url)
    enqueue(email_question_author, answer.pk, url)


def enqueue(task, *args):
    try:
        task.delay(*args)
    except OperationalError:
        logger.exception('Could not enqueue %s', task.name)


@login_required
def add_answer(request, question):
    form = AnswerForm(request.POST)
    if form.is_valid():
        answer = form.save(author=request.user, question=question)
        url = answer.get_page_url(ANSWERS_PER_PAGE)
        transaction.on_commit(lambda: enqueue_answer_jobs(answer, url))
        return redirect(url)
    return render_question(request, question, form)


def render_question(request, question, form):
    answers = Answer.objects.for_question(question).with_vote(request.user)
    page = paginate(answers, request, per_page=ANSWERS_PER_PAGE)
    return render(request, 'questions/question.html', {
        'question': question,
        'page': page,
        'form': form,
        'websocket_url': settings.CENTRIFUGO_WS_URL if settings.CENTRIFUGO_TOKEN_SECRET else '',
        'channel': question_channel(question.pk),
    })


@require_GET
@never_cache
def websocket_token(request):
    if not settings.CENTRIFUGO_TOKEN_SECRET:
        raise Http404
    claims = {
        'sub': str(request.user.pk) if request.user.is_authenticated else '',
        'exp': int(time.time()) + 300,
    }
    return JsonResponse({'token': jwt.encode(claims, settings.CENTRIFUGO_TOKEN_SECRET, algorithm='HS256')})


@require_GET
@never_cache
def answer_card(request, question_id, answer_id):
    answers = Answer.objects.select_related('author__profile', 'question').with_vote(request.user)
    answer = get_object_or_404(answers, pk=answer_id, question_id=question_id)
    return render(request, 'questions/includes/answer_card.html', {'answer': answer, 'question': answer.question})


def question(request, question_id):
    items = Question.objects.for_display().with_vote(request.user)
    question = get_object_or_404(items, pk=question_id)
    if request.method == 'POST':
        return add_answer(request, question)
    return render_question(request, question, AnswerForm())


@login_required
def ask(request):
    form = QuestionForm(request.POST if request.method == 'POST' else None)
    if form.is_valid():
        return redirect(form.save(author=request.user))
    return render(request, 'questions/ask.html', {'form': form})


def handle_ajax_form(request, form_class):
    if request.method != 'POST':
        return JsonResponse({'error': 'Используйте POST.'}, status=405, headers={'Allow': 'POST'})
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Войдите, чтобы выполнить это действие.'}, status=401)

    form = form_class(request.POST)
    if not form.is_valid():
        errors = [message for messages in form.errors.values() for message in messages]
        return JsonResponse({'error': ' '.join(errors)}, status=400)

    try:
        result = form.save(user=request.user)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'Вопрос или ответ не найден.'}, status=404)
    except PermissionError:
        return JsonResponse({'error': 'Выбрать правильный ответ может только автор вопроса.'}, status=403)
    if result.get('duplicate'):
        return JsonResponse({**result, 'error': 'Вы уже поставили эту оценку.'}, status=409)
    return JsonResponse(result)


def vote(request):
    return handle_ajax_form(request, VoteForm)


def correct_answer(request):
    return handle_ajax_form(request, CorrectAnswerForm)


def csrf_failure(request, reason=''):
    match = request.resolver_match
    if match and match.url_name in {'vote', 'correct_answer'}:
        return JsonResponse({'error': 'Обновите страницу и попробуйте ещё раз.'}, status=403)
    return default_csrf_failure(request, reason=reason)
