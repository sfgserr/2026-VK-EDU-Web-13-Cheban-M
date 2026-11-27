from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings

from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


@override_settings(DEBUG=False)
class QuestionTests(TestCase):
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
        with self.assertNumQueries(5):
            response = self.client.get('/')
        self.assertEqual(response.context['page'][0].pk, Question.objects.newest().first().pk)
        response = self.client.get('/hot/')
        ratings = [question.rating for question in response.context['page']]
        self.assertEqual(ratings, sorted(ratings, reverse=True))
        for value, number in [('abc', 1), ('999', 3), ('-1', 3), ('2', 2)]:
            self.assertEqual(self.client.get('/', {'page': value}).context['page'].number, number)
        question = Question.objects.first()
        Answer.objects.bulk_create([Answer(question=question, author=question.author, text='Ещё ответ') for _ in range(5)])
        with self.assertNumQueries(6):
            response = self.client.get(question.get_absolute_url(), {'page': 2})
        self.assertEqual(len(response.context['page']), 5)
        tag = Tag.objects.first()
        response = self.client.get(tag.get_absolute_url())
        for question in response.context['page']:
            self.assertIn(tag, question.tags.all())
