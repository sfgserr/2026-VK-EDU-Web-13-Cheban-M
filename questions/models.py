from django.conf import settings
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse


class TagManager(models.Manager):
    def popular(self):
        return self.annotate(total=models.Count('questions')).order_by('-total', 'name')[:8]


class Tag(models.Model):
    name = models.CharField('Название', max_length=64, unique=True)
    objects = TagManager()

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tag', args=[self.name])


class VoteQuerySet(models.QuerySet):
    def with_vote(self, user):
        if not user.is_authenticated:
            return self
        vote = self.model._meta.get_field('likes').related_model.objects.filter(
            user=user, **{self.model._meta.model_name: models.OuterRef('pk')},
        )
        return self.annotate(vote=models.Subquery(vote.values('value')[:1]))


class QuestionQuerySet(VoteQuerySet):
    def for_display(self):
        counts = (
            Answer.objects.filter(question_id=models.OuterRef('pk'))
            .values('question_id').annotate(total=models.Count('id')).values('total')
        )
        return (
            self.select_related('author', 'author__profile').prefetch_related('tags')
            .annotate(answers_count=Coalesce(models.Subquery(counts), 0))
        )

    def newest(self):
        return self.for_display().order_by('-created_at', '-id')

    def best(self):
        return self.for_display().order_by('-rating', '-id')

    def by_tag(self, tag):
        return self.best().filter(tags=tag)


class Question(models.Model):
    title = models.CharField('Заголовок', max_length=255)
    text = models.TextField('Текст')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='questions', verbose_name='Автор')
    tags = models.ManyToManyField(Tag, related_name='questions', verbose_name='Теги', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    rating = models.IntegerField('Рейтинг', default=0, db_index=True)
    objects = QuestionQuerySet.as_manager()

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['-created_at', '-id']), models.Index(fields=['-rating', '-id'])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('question', args=[self.pk])


class AnswerQuerySet(VoteQuerySet):
    def for_question(self, question):
        return self.filter(question=question).select_related('author', 'author__profile').order_by('-rating', 'created_at', 'id')


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers', verbose_name='Вопрос')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='answers', verbose_name='Автор')
    text = models.TextField('Текст')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    rating = models.IntegerField('Рейтинг', default=0)
    correct = models.BooleanField('Правильный ответ', default=False)
    objects = AnswerQuerySet.as_manager()

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'
        indexes = [models.Index(fields=['question', '-rating', 'created_at'])]

    def __str__(self):
        return self.text[:80]

    def get_page_url(self, per_page):
        # Same ordering as AnswerQuerySet.for_question().
        preceding = self.question.answers.filter(
            models.Q(rating__gt=self.rating)
            | models.Q(rating=self.rating, created_at__lt=self.created_at)
            | models.Q(rating=self.rating, created_at=self.created_at, pk__lt=self.pk)
        ).count()
        page = preceding // per_page + 1
        return f'{self.question.get_absolute_url()}?page={page}#answer-{self.pk}'


class QuestionLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='likes', verbose_name='Вопрос')
    value = models.SmallIntegerField('Оценка', choices=[(-1, 'Дизлайк'), (1, 'Лайк')], default=1)

    class Meta:
        verbose_name = 'Оценка вопроса'
        verbose_name_plural = 'Оценки вопросов'
        unique_together = [('user', 'question')]
        constraints = [models.CheckConstraint(check=models.Q(value__in=[-1, 1]), name='question_like_value')]

    def __str__(self):
        return f'{self.user_id}: {self.question_id} ({self.value})'


class AnswerLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='likes', verbose_name='Ответ')
    value = models.SmallIntegerField('Оценка', choices=[(-1, 'Дизлайк'), (1, 'Лайк')], default=1)

    class Meta:
        verbose_name = 'Оценка ответа'
        verbose_name_plural = 'Оценки ответов'
        unique_together = [('user', 'answer')]
        constraints = [models.CheckConstraint(check=models.Q(value__in=[-1, 1]), name='answer_like_value')]

    def __str__(self):
        return f'{self.user_id}: {self.answer_id} ({self.value})'
