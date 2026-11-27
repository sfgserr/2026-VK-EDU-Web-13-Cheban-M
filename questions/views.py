from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.csrf import csrf_failure as default_csrf_failure

from core.utils import paginate
from questions.forms import AnswerForm, CorrectAnswerForm, QuestionForm, VoteForm
from questions.models import Answer, Question, Tag

ANSWERS_PER_PAGE = 10


def index(request):
    page = paginate(Question.objects.newest().with_vote(request.user), request)
    return render(request, 'questions/index.html', {'page': page})


def hot(request):
    page = paginate(Question.objects.best().with_vote(request.user), request)
    return render(request, 'questions/hot.html', {'page': page})


def tag(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name)
    page = paginate(Question.objects.by_tag(tag).with_vote(request.user), request)
    return render(request, 'questions/tag.html', {'page': page, 'tag_name': tag.name})


@login_required
def add_answer(request, question):
    form = AnswerForm(request.POST)
    if form.is_valid():
        answer = form.save(author=request.user, question=question)
        return redirect(answer.get_page_url(ANSWERS_PER_PAGE))
    return render_question(request, question, form)


def render_question(request, question, form):
    answers = Answer.objects.for_question(question).with_vote(request.user)
    page = paginate(answers, request, per_page=ANSWERS_PER_PAGE)
    return render(request, 'questions/question.html', {'question': question, 'page': page, 'form': form})


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
