from rest_framework import serializers
from core.models import User, Quest, PromoCode, UserQuestProgress


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'telegram_id', 'name', 'phone_number', 'is_verified', 'created_at']


class QuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quest
        fields = ['id', 'name', 'description', 'location', 'created_at', 'is_active']


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'quest', 'is_used', 'created_at']


class UserQuestProgressSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    quest = QuestSerializer(read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = UserQuestProgress
        fields = [
            'id', 'user', 'quest', 'photo', 'status',
            'promo_code', 'completed_at', 'admin_comment'
        ] 