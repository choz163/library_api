"""
models.py

Модели приложения библиотеки: Author, Book, Loan.
"""

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class Author(models.Model):
    """
    Модель автора книги.
    Поле:
        name (CharField): Имя автора, уникальное.
    """
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        """
        Возвращает строковое представление автора (его имя).
        """
        return self.name

class Book(models.Model):
    """
    Модель книги.
    Поля:
        title (CharField): Название книги.
        authors (ManyToManyField): Авторы книги.
        genre (CharField): Жанр (опционально).
        description (TextField): Описание (опционально).
        available (BooleanField): Доступность для займа.
    """
    title = models.CharField(max_length=255)
    authors = models.ManyToManyField(Author, related_name="books")
    genre = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        """
        Возвращает строковое представление книги (ее название).
        """
        return self.title

class Loan(models.Model):
    """
    Модель займа книги.
    Поля:
        user (ForeignKey): Пользователь, взявший книгу.
        book (ForeignKey): Книга, которая была взята.
        loan_date (DateTimeField): Дата и время выдачи (авто).
        return_date (DateTimeField): Дата и время возврата (опционально).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loans")
    loan_date = models.DateTimeField(auto_now_add=True)
    return_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        """
        Определяем уникальность комбинации (user, book, loan_date).
        """
        unique_together = ("user", "book", "loan_date")

    def __str__(self):
        """
        Возвращает строку вида "Название книги → имя пользователя".
        """
        return f"{self.book.title} → {self.user.username}"

    @property
    def status(self):
        """
        Свойство статуса займа.
        Возвращает 'returned', если книга возвращена (return_date не None),
        иначе 'borrowed'.
        """
        return "returned" if self.return_date else "borrowed"
