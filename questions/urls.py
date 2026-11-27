from django.urls import path

from questions import views

urlpatterns = [
    path('', views.index, name='index'),
    path('hot/', views.hot, name='hot'),
    path('tag/<str:tag_name>/', views.tag, name='tag'),
    path('question/<int:question_id>/', views.question, name='question'),
    path('ajax/vote/', views.vote, name='vote'),
    path('ajax/correct-answer/', views.correct_answer, name='correct_answer'),
    path('ask/', views.ask, name='ask'),
]
