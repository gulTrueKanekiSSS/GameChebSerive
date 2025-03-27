from django.contrib import admin
from .models import User, Quest, PromoCode, UserQuestProgress


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'phone_number', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('name', 'telegram_id', 'phone_number')


@admin.register(Quest)
class QuestAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'location')


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'quest', 'is_used', 'created_at')
    list_filter = ('is_used', 'quest', 'created_at')
    search_fields = ('code',)


@admin.register(UserQuestProgress)
class UserQuestProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'quest', 'status', 'completed_at')
    list_filter = ('status', 'completed_at')
    search_fields = ('user__name', 'quest__name', 'admin_comment')
    raw_id_fields = ('user', 'quest', 'promo_code') 