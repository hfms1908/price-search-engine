from django.urls import path
from .views import home, warmup

urlpatterns = [
    path("", home, name="home"),
    path("warmup/", warmup, name="warmup"),
]
