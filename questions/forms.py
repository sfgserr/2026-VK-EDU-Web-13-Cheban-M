from django import forms
from django.db import transaction
from django.db.models import F

from core.forms import BootstrapFormMixin
from core.models import Profile
from questions.models import Answer, AnswerLike, Question, QuestionLike, Tag


class QuestionForm(BootstrapFormMixin, forms.ModelForm):
    title = forms.CharField(label='Заголовок', max_length=150)
    text = forms.CharField(label='Текст', max_length=5000, widget=forms.Textarea(attrs={'rows': 6}))
    tags = forms.CharField(label='Теги', required=False, help_text='Через запятую, не более 3 тегов.')

    class Meta:
        model = Question
        fields = ('title', 'text')

    def clean_tags(self):
        names = dict.fromkeys(name.strip() for name in self.cleaned_data['tags'].split(',') if name.strip())
        if len(names) > 3:
            raise forms.ValidationError('Укажите не более трёх тегов.')
        for name in names:
            if len(name) > 64 or name in {'.', '..'} or any(c in '/\\' or not c.isprintable() for c in name):
                raise forms.ValidationError('Тег должен содержать до 64 символов, без косых черт и управляющих символов.')
        return list(names)

    @transaction.atomic
    def save(self, *, author):
        question = super().save(commit=False)
        question.author = author
        question.save()
        tags = [Tag.objects.get_or_create(name=name)[0] for name in sorted(self.cleaned_data['tags'])]
        question.tags.set(tags)
        return question


class AnswerForm(BootstrapFormMixin, forms.ModelForm):
    text = forms.CharField(label='Ваш ответ', max_length=5000, widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Answer
        fields = ('text',)

    def save(self, *, author, question):
        answer = super().save(commit=False)
        answer.author = author
        answer.question = question
        answer.save()
        return answer


class VoteForm(forms.Form):
    kind = forms.ChoiceField(choices=[('question', 'Вопрос'), ('answer', 'Ответ')])
    target_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    value = forms.TypedChoiceField(choices=[(-1, 'Дизлайк'), (1, 'Лайк')], coerce=int)

    @transaction.atomic
    def save(self, *, user):
        kind = self.cleaned_data['kind']
        model, vote_model = (Question, QuestionLike) if kind == 'question' else (Answer, AnswerLike)
        target = model.objects.select_for_update().get(pk=self.cleaned_data['target_id'])
        value = self.cleaned_data['value']
        lookup = {kind: target, 'user': user}
        vote, created = vote_model.objects.get_or_create(**lookup, defaults={'value': value})
        if not created and vote.value == value:
            return {'rating': target.rating, 'vote': value, 'duplicate': True}

        delta = value if created else value - vote.value
        if not created:
            vote.value = value
            vote.save(update_fields=['value'])
        target.rating += delta
        target.save(update_fields=['rating'])
        Profile.objects.filter(user_id=target.author_id).update(rating=F('rating') + delta)
        return {'rating': target.rating, 'vote': value}


class CorrectAnswerForm(forms.Form):
    question_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    answer_id = forms.IntegerField(min_value=1, max_value=2**63 - 1)
    correct = forms.TypedChoiceField(choices=[('1', 'Да'), ('0', 'Нет')], coerce=lambda value: value == '1')

    @transaction.atomic
    def save(self, *, user):
        question = Question.objects.select_for_update().get(pk=self.cleaned_data['question_id'])
        if question.author_id != user.pk:
            raise PermissionError
        answer = question.answers.get(pk=self.cleaned_data['answer_id'])
        correct = self.cleaned_data['correct']
        if correct:
            question.answers.filter(correct=True).exclude(pk=answer.pk).update(correct=False)
        answer.correct = correct
        answer.save(update_fields=['correct'])
        return {'answer_id': answer.pk, 'correct': correct}
