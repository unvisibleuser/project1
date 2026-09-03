from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path('generate/', views.GeneratePromptView.as_view(), name='generate-prompt'),
]