from django.http import Http404
from django.shortcuts import render

from core.utils import paginate

TAGS = ['python', 'django', 'mysql', 'css', 'bootstrap', 'git']
VOTE_STATES = ['like', None, 'dislike']

QUESTIONS = [
    {
        'id': i,
        'title': f'Вопрос номер {i}',
        'text': f'Текст вопроса номер {i}. Подскажите, как это сделать правильно?',
        'rating': (i * 7) % 30 - 5,
        'vote': VOTE_STATES[i % 3],
        'answers_count': i % 5,
        'tags': [TAGS[i % len(TAGS)], TAGS[(i + 2) % len(TAGS)]],
    }
    for i in range(1, 51)
]

ANSWERS = [
    {
        'id': i,
        'text': f'Текст ответа номер {i}.',
        'rating': 20 - i,
        'vote': VOTE_STATES[i % 3],
        'correct': i == 1,
    }
    for i in range(1, 14)
]


def index(request):
    page = paginate(QUESTIONS, request)
    return render(request, 'questions/index.html', {'page': page})


def hot(request):
    questions = sorted(QUESTIONS, key=lambda q: q['rating'], reverse=True)
    page = paginate(questions, request)
    return render(request, 'questions/hot.html', {'page': page})


def tag(request, tag_name):
    questions = [q for q in QUESTIONS if tag_name in q['tags']]
    page = paginate(questions, request)
    return render(request, 'questions/tag.html', {'page': page, 'tag_name': tag_name})


def question(request, question_id):
    if not 1 <= question_id <= len(QUESTIONS):
        raise Http404('Вопрос не найден')
    page = paginate(ANSWERS, request)
    return render(request, 'questions/question.html', {
        'question': QUESTIONS[question_id - 1],
        'page': page,
    })


def ask(request):
    return render(request, 'questions/ask.html')
