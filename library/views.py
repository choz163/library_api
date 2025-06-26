from django.contrib.auth import get_user_model
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Author, Book, Loan
from .permissions import IsAdminOrReadOnly
from .serializers import (AuthorSerializer, BookSerializer, LoanSerializer,
                          RegisterSerializer, UserSerializer)


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticated]

    # разрешаем anonymous только на list/retrieve
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return super().get_permissions()

    # если надо поиск и сортировку по авторам
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["name"]  # фильтрация ?name=…
    search_fields = ["name"]  # поиск ?search=…
    ordering_fields = ["name", "birth_date"]  # сортировка ?ordering=name,-birth_date


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Фильтруем по жанру, по доступности и по авторам (m2m)
    filterset_fields = ["genre", "available", "authors"]

    # Поиск по названию и описанию
    search_fields = ["title", "description"]

    # Разрешаем сортировать по title
    ordering_fields = ["title"]


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    # фильтрация/поиск/сортировка
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        "book",  # ?book=5
        "user",  # (staff only) ?user=2
        "return_date",  # ?returned_at__isnull=True
        "loan_date",  # > / < поиск по дате
    ]
    search_fields = [
        "book__title",
        "user__username",
    ]
    ordering_fields = [
        "loan_date",
        "return_date",
    ]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset.all()
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        book = serializer.validated_data["book"]
        if not book.available:
            raise ValidationError("Книга недоступна")
        book.available = False
        book.save()
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def return_book(self, request, pk=None):
        loan = self.get_object()
        if loan.return_date:
            return Response(
                {"detail": "Эта книга уже возвращена."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        loan.return_date = timezone.now()
        loan.save()
        loan.book.available = True
        loan.book.save()
        return Response({"status": "Возвращена"})


class RegisterView(generics.CreateAPIView):
    queryset = None
    serializer_class = RegisterSerializer
    permission_classes = []


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminOrReadOnly]

    # если нужен поиск/фильтрация по юзерам
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["username", "email", "is_staff"]
    search_fields = ["username", "email"]
    ordering_fields = ["username", "date_joined"]


class TokenView(TokenObtainPairView):
    permission_classes = []
