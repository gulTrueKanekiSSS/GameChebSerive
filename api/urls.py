from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    QuestViewSet,
    PromoCodeViewSet,
    UserQuestProgressViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'quests', QuestViewSet)
router.register(r'promocodes', PromoCodeViewSet)
router.register(r'progress', UserQuestProgressViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 