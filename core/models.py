import uuid
from django.db import models


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_route_builder = models.BooleanField(default=False, help_text="Может создавать новые маршруты")

    def __str__(self):
        return f"{self.name} ({self.telegram_id})"


class Quest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=255)
    latitude = models.FloatField(null=True, blank=True, help_text="Широта")
    longitude = models.FloatField(null=True, blank=True, help_text="Долгота")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PromoCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE, related_name='promocodes')
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.quest.name})"


class UserQuestProgress(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'На проверке'
        APPROVED = 'approved', 'Подтверждено'
        REJECTED = 'rejected', 'Отклонено'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quest_progress')
    quest = models.ForeignKey(Quest, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='quest_photos/')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)
    admin_comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'quest')

    def __str__(self):
        return f"{self.user.name} - {self.quest.name} ({self.status})"

class Route(models.Model):
    """
    Маршрут — упорядоченный набор квестов.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class RouteQuest(models.Model):
    """
    Связь Route → Quest с порядком и дополнительными полями.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='route_quests'
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.CASCADE,
        related_name='+'
    )
    order = models.PositiveSmallIntegerField(
        help_text="Позиция квеста в маршруте (1, 2, 3…)"
    )
    hint_text = models.TextField(blank=True, help_text="Подсказка для точки")
    photo = models.ImageField(
        upload_to='route_quest_photos/',
        blank=True, null=True
    )
    audio = models.FileField(
        upload_to='route_quest_audio/',
        blank=True, null=True
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('route', 'quest')
        ordering = ['order']
        indexes = [
            models.Index(fields=['route', 'order']),
        ]

    def __str__(self):
        return f"{self.route.name} → {self.order}. {self.quest.name}"