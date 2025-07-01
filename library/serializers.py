from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Author, Book, Loan

User = get_user_model()

class AuthorSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Author.
    Поля: id, name.
    """
    class Meta:
        model = Author
        fields = ["id", "name"]

class BookSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Book.
    Чтение:
        authors — вложенный список авторов.
    Запись:
        author_ids — список ID авторов.
    """
    authors = AuthorSerializer(many=True, read_only=True)
    author_ids = serializers.PrimaryKeyRelatedField(
        source='authors',
        many=True,
        queryset=Author.objects.all(),
        write_only=True
    )

    class Meta:
        model = Book
        fields = ("id", "title", "genre", "description", "available", "authors", "author_ids")

class LoanSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели Loan.
    Поля:
        id, user (текущий пользователь по умолчанию),
        book, loan_date, return_date, status.
    """
    user = serializers.PrimaryKeyRelatedField(
        default=serializers.CurrentUserDefault(),
        queryset=User.objects.all()
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ("id", "user", "book", "loan_date", "return_date", "status")
        read_only_fields = ("loan_date", "return_date", "status")

    def get_status(self, obj):
        """
        Возвращает статус займа:
        - 'вернули' если возвращена,
        - 'на руках' если в пользовании.
        """
        return "вернули" if obj.return_date else "на руках"

class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор модели User.
    Поля: id, username, email.
    """
    class Meta:
        model = User
        fields = ["id", "username", "email"]

class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя.
    Поля: username, email, password.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        """
        Создает нового пользователя с хэшированием пароля.
        """
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )
