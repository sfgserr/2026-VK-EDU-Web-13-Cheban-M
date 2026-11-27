from django.urls import path

from questions import views

urlpatterns = [
    path('', views.index, name='index'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('realtime/token/', views.websocket_token, name='websocket_token'),
    path('question/<int:question_id>/answers/<int:answer_id>/', views.answer_card, name='answer_card'),
    path('hot/', views.hot, name='hot'),
    path('tag/<str:tag_name>/', views.tag, name='tag'),
    path('question/<int:question_id>/', views.question, name='question'),
    path('ajax/vote/', views.vote, name='vote'),
    path('ajax/correct-answer/', views.correct_answer, name='correct_answer'),
    path('ask/', views.ask, name='ask'),
]
