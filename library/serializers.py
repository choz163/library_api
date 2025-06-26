from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Author, Book, Loan

User = get_user_model()


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name"]


class BookSerializer(serializers.ModelSerializer):
    # для чтения: вложенные объекты
    authors = AuthorSerializer(many=True, read_only=True)
    # для записи: список PK (id) авторов
    author_ids = serializers.PrimaryKeyRelatedField(
        source='authors',
        many=True,
        queryset=Author.objects.all(),
        write_only=True
    )

    class Meta:
        model = Book
        fields = ('id','title','genre','description','available','authors','author_ids')


class LoanSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        default=serializers.CurrentUserDefault(), queryset=User.objects.all()
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = ("id", "user", "book", "loan_date", "return_date", "status")
        read_only_fields = ("loan_date", "return_date", "status")

    def get_status(self, obj):
        return "вернули" if obj.return_date else "на руках"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
        )
        return user
