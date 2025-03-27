from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.models import User, Quest, PromoCode, UserQuestProgress
from .serializers import (
    UserSerializer,
    QuestSerializer,
    PromoCodeSerializer,
    UserQuestProgressSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class QuestViewSet(viewsets.ModelViewSet):
    queryset = Quest.objects.all()
    serializer_class = QuestSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        quest = self.get_object()
        quest.is_active = not quest.is_active
        quest.save()
        return Response({'status': 'success'})


class PromoCodeViewSet(viewsets.ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAdminUser]


class UserQuestProgressViewSet(viewsets.ModelViewSet):
    queryset = UserQuestProgress.objects.all()
    serializer_class = UserQuestProgressSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        progress = self.get_object()
        
        if progress.status != UserQuestProgress.Status.PENDING:
            return Response(
                {'error': 'Этот квест уже проверен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Находим неиспользованный промокод для этого квеста
        promo_code = PromoCode.objects.filter(
            quest=progress.quest,
            is_used=False
        ).first()

        if not promo_code:
            return Response(
                {'error': 'Нет доступных промокодов для этого квеста'},
                status=status.HTTP_400_BAD_REQUEST
            )

        progress.status = UserQuestProgress.Status.APPROVED
        progress.promo_code = promo_code
        progress.admin_comment = request.data.get('comment', '')
        progress.save()

        promo_code.is_used = True
        promo_code.save()

        return Response({'status': 'success'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        progress = self.get_object()
        
        if progress.status != UserQuestProgress.Status.PENDING:
            return Response(
                {'error': 'Этот квест уже проверен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        progress.status = UserQuestProgress.Status.REJECTED
        progress.admin_comment = request.data.get('comment', '')
        progress.save()

        return Response({'status': 'success'}) 