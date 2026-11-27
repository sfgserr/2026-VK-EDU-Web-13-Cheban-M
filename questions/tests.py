from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.models import Profile
from core.sidebar import BEST_MEMBERS_KEY, POPULAR_TAGS_KEY
from core.tasks import refresh_best_members, refresh_popular_tags
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


@override_settings(
    DEBUG=False,
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class QuestionTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_empty_pages_and_missing_objects(self):
        self.assertContains(self.client.get('/'), 'Вопросов пока нет')
        for url in ['/hot/', '/login/', '/signup/']:
            self.assertEqual(self.client.get(url).status_code, 200)
        for url in ['/profile/', '/ask/']:
            self.assertRedirects(self.client.get(url), f'/login/?next={url}', fetch_redirect_response=False)
        for url in ['/question/1/', '/question/abc/', '/tag/missing/']:
            self.assertEqual(self.client.get(url).status_code, 404)
        user = User.objects.create_user('author')
        question = Question.objects.create(author=user, title='Вопрос', text='Текст')
        tag = Tag.objects.create(name='python')
        self.assertContains(self.client.get(question.get_absolute_url()), 'Пока нет ни одного ответа')
        self.assertContains(self.client.get(tag.get_absolute_url()), 'Вопросов пока нет')

    def test_fill_db_counts_ratings_and_unique_votes(self):
        call_command('fill_db', 2, stdout=StringIO())
        self.assertEqual([model.objects.count() for model in [User, Profile, Question, Answer, Tag]], [2, 2, 20, 200, 2])
        self.assertEqual(QuestionLike.objects.count() + AnswerLike.objects.count(), 400)
        question = Question.objects.for_display().first()
        self.assertEqual(question.answers_count, question.answers.count())
        self.assertEqual(question.rating, sum(question.likes.values_list('value', flat=True)))
        for model, field in [(QuestionLike, 'question_id'), (AnswerLike, 'answer_id')]:
            vote = model.objects.first()
            with self.assertRaises(IntegrityError), transaction.atomic():
                model.objects.create(user_id=vote.user_id, **{field: getattr(vote, field)})
        call_command('fill_db', 2, stdout=StringIO())
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(QuestionLike.objects.count() + AnswerLike.objects.count(), 800)

    def test_pagination_sorting_and_query_count(self):
        call_command('fill_db', 3, stdout=StringIO())
        self.client.get('/')  # Fill the sidebar cache before measuring page queries.
        with self.assertNumQueries(3):
            response = self.client.get('/')
        self.assertEqual(response.context['page'][0].pk, Question.objects.newest().first().pk)
        response = self.client.get('/hot/')
        ratings = [question.rating for question in response.context['page']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))
        for value, number in [('abc', 1), ('999', 3), ('-1', 3), ('2', 2)]:
            self.assertEqual(self.client.get('/', {'page': value}).context['page'].number, number)
        question = Question.objects.first()
        Answer.objects.bulk_create([Answer(question=question, author=question.author, text='Ещё ответ') for _ in range(5)])
        with self.assertNumQueries(4):
            response = self.client.get(question.get_absolute_url(), {'page': 2})
        self.assertEqual(len(response.context['page']), 5)
        tag = Tag.objects.first()
        response = self.client.get(tag.get_absolute_url())
        for question in response.context['page']:
            self.assertIn(tag, question.tags.all())

    def test_search_suggestions_by_title_and_body(self):
        user = User.objects.create_user('author')
        title_match = Question.objects.create(author=user, title='Настройка Django', text='Установка пакета')
        body_match = Question.objects.create(author=user, title='Развёртывание', text='Сервер Django с Redis')
        irrelevant = Question.objects.create(author=user, title='Flask', text='Другой фреймворк')
        url = reverse('search_suggestions')
        result = self.client.get(url, {'q': 'djan'}).json()['results']
        self.assertCountEqual([item['url'] for item in result], [
            title_match.get_absolute_url(), body_match.get_absolute_url(),
        ])
        self.assertEqual(self.client.get(url, {'q': 'настройка django'}).json()['results'][0]['url'],
                         title_match.get_absolute_url())
        self.assertEqual(self.client.get(url, {'q': 'и или'}).json(), {'results': []})
        self.assertNotContains(self.client.get('/', {'q': 'redis'}), irrelevant.title)

    def test_sidebar_miss_and_periodic_refresh(self):
        now = timezone.now()
        user = User.objects.create_user('recent', first_name='Недавний участник')
        other = User.objects.create_user('old', first_name='Бывший участник')
        recent = Question.objects.create(author=user, title='Новый', text='Пример', rating=5)
        old = Question.objects.create(author=other, title='Старый', text='Пример', rating=1000)
        Question.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=110))
        recent.tags.create(name='recent-tag')
        old.tags.create(name='old-tag')

        self.assertIsNone(cache.get(POPULAR_TAGS_KEY))
        self.client.get('/')
        self.assertEqual(cache.get(POPULAR_TAGS_KEY), ['recent-tag'])
        self.assertEqual(cache.get(BEST_MEMBERS_KEY), ['Недавний участник'])
        Answer.objects.create(author=other, question=recent, text='Новый ответ', rating=10)
        recent.tags.create(name='new-tag')

        self.assertEqual(cache.get(POPULAR_TAGS_KEY), ['recent-tag'])
        refresh_popular_tags()
        refresh_best_members()
        self.assertEqual(cache.get(POPULAR_TAGS_KEY), ['new-tag', 'recent-tag'])
        self.assertEqual(cache.get(BEST_MEMBERS_KEY), ['Бывший участник', 'Недавний участник'])

    @override_settings(CENTRIFUGO_API_KEY='local-test-key')
    def test_answer_jobs_are_queued_after_commit(self):
        author = User.objects.create_user('author')
        question = Question.objects.create(author=author, title='Вопрос', text='Текст')
        self.client.force_login(author)
        with patch('questions.views.publish_answer.delay') as publish, patch('questions.views.email_question_author.delay') as email:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(question.get_absolute_url(), {'text': 'Ответ'})
                self.assertEqual(response.status_code, 302)
                publish.assert_not_called()
                email.assert_not_called()
            answer = Answer.objects.get(question=question)
            publish.assert_called_once_with(question.pk, answer.pk, response['Location'])
            email.assert_called_once_with(answer.pk, response['Location'])
