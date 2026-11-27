from collections import Counter
from itertools import islice
import random
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum
from faker import Faker

from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


def insert(model, objects, collect_ids=False):
    objects = iter(objects)
    ids = []
    while True:
        batch = list(islice(objects, 2000))
        if not batch:
            return ids
        created = model.objects.bulk_create(batch, batch_size=2000)
        if collect_ids:
            ids.extend(obj.pk for obj in created)


def update_ratings(model, ratings):
    items = iter(ratings.items())
    while True:
        batch = list(islice(items, 2000))
        if not batch:
            return
        model.objects.bulk_update([model(pk=pk, rating=value) for pk, value in batch], ['rating'], batch_size=2000)


class Command(BaseCommand):
    help = 'Добавить ratio пользователей, 10*ratio вопросов, 100*ratio ответов, ratio тегов и 200*ratio оценок.'

    def add_arguments(self, parser):
        parser.add_argument('ratio', type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        ratio = options['ratio']
        if ratio < 2:
            raise CommandError('ratio должен быть не меньше 2: иначе невозможно создать 200 уникальных оценок на пользователя.')
        fake = Faker('ru_RU')
        prefix = uuid4().hex[:12]
        texts = [fake.paragraph(nb_sentences=4) for _ in range(1000)]
        titles = [fake.sentence(nb_words=7) for _ in range(1000)]
        self.stdout.write('Создание пользователей и тегов...')
        users = insert(User, (User(username=f'{prefix}_{i}', email=f'{prefix}_{i}@example.com', password='!', first_name=fake.first_name(), last_name=fake.last_name()) for i in range(ratio)), True)
        insert(Profile, (Profile(user_id=pk) for pk in users))
        tags = insert(Tag, (Tag(name=f'{fake.word()}-{prefix}-{i}') for i in range(ratio)), True)
        self.stdout.write('Создание вопросов и ответов...')
        questions = insert(Question, (Question(title=random.choice(titles), text=random.choice(texts), author_id=random.choice(users)) for _ in range(ratio * 10)), True)
        insert(Question.tags.through, (Question.tags.through(question_id=pk, tag_id=tag) for pk in questions for tag in random.sample(tags, min(3, ratio))))
        answers = insert(Answer, (Answer(question_id=pk, author_id=random.choice(users), text=random.choice(texts), correct=(j == 0)) for pk in questions for j in range(10)), True)
        question_ratings, answer_ratings = Counter(), Counter()

        def votes(model, targets, count, field, ratings):
            # Each (user, target) pair occurs once; no per-row database queries.
            for i in range(count):
                target = targets[i % len(targets)]
                user = users[i // len(targets)]
                value = random.choice([-1, 1])
                ratings[target] += value
                yield model(user_id=user, value=value, **{field: target})

        self.stdout.write('Создание оценок...')
        insert(QuestionLike, votes(QuestionLike, questions, ratio * 10, 'question_id', question_ratings))
        insert(AnswerLike, votes(AnswerLike, answers, ratio * 190, 'answer_id', answer_ratings))
        self.stdout.write('Обновление рейтингов...')
        update_ratings(Question, question_ratings)
        update_ratings(Answer, answer_ratings)
        # Profile rating is the sum of ratings of the author's questions and answers.
        totals = Counter()
        for model in (Question, Answer):
            for row in model.objects.filter(author_id__in=users).values('author_id').annotate(total=Sum('rating')):
                totals[row['author_id']] += row['total'] or 0
        profiles = list(Profile.objects.filter(user_id__in=users))
        for profile in profiles:
            profile.rating = totals[profile.user_id]
        Profile.objects.bulk_update(profiles, ['rating'], batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f'Добавлено: {ratio} пользователей, {ratio * 10} вопросов, {ratio * 100} ответов, {ratio} тегов, {ratio * 200} оценок.'))
