from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from library.models import Author, Book, Loan

User = get_user_model()


class BaseTestCase(APITestCase):
    def setUp(self):
        # создаём администратора (is_staff=True)
        self.admin = User.objects.create_superuser("admin", password="pass")
        assert self.client.login(username="admin", password="pass")
        # и ещё обычного пользователя
        self.user = User.objects.create_user("user", password="pass2")


class AuthorTests(BaseTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("foo", "foo@bar.com", "secret")
        self.client.force_authenticate(user=self.user)

    def test_create_author(self):
        url = reverse("author-list")
        resp = self.client.post(url, {"name": "Tolstoy"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_list_and_retrieve_anonymous(self):
        a1 = Author.objects.create(name="A1")
        a2 = Author.objects.create(name="A2")
        self.client.logout()
        # list
        resp = self.client.get(reverse("author-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)
        # retrieve
        resp2 = self.client.get(reverse("author-detail", args=[a1.id]))
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.data["name"], "A1")

    def test_update_and_partial_delete(self):
        a = Author.objects.create(name="Original")
        # full update
        resp = self.client.put(
            reverse("author-detail", args=[a.id]), {"name": "NewName"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        a.refresh_from_db()
        self.assertEqual(a.name, "NewName")
        # partial update
        resp2 = self.client.patch(reverse("author-detail", args=[a.id]), {"name": "XX"})
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        a.refresh_from_db()
        self.assertEqual(a.name, "XX")
        # delete
        resp3 = self.client.delete(reverse("author-detail", args=[a.id]))
        self.assertEqual(resp3.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Author.objects.filter(id=a.id).exists())

    def test_filter_search_ordering(self):
        Author.objects.bulk_create(
            [
                Author(name="Leo"),
                Author(name="Lev"),
                Author(name="Mark"),
            ]
        )
        # filter by exact name
        resp = self.client.get(reverse("author-list") + "?name=Lev")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        # search (icontains)
        resp2 = self.client.get(reverse("author-list") + "?search=Le")
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["count"], 2)
        # ordering
        resp3 = self.client.get(reverse("author-list") + "?ordering=-name")
        names = [o["name"] for o in resp3.data["results"]]
        self.assertEqual(names, sorted(names, reverse=True))


class BookTests(BaseTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user("foo", "foo@bar.com", "secret")
        self.client.force_authenticate(user=self.user)
        self.a1 = Author.objects.create(name="A1")
        self.a2 = Author.objects.create(name="A2")

    def test_create_book(self):
        url = reverse("book-list")
        data = {
            "title": "War and Peace",
            "genre": "Novel",
            "description": "Epic",
            "available": True,
            "author_ids": [self.a1.id, self.a2.id],
        }
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        b = Book.objects.first()
        self.assertEqual(b.title, "War and Peace")
        self.assertEqual(list(b.authors.all()), [self.a1, self.a2])

    def test_list_and_retrieve_anonymous(self):
        b = Book.objects.create(title="B1", genre="X", description="", available=True)
        b.authors.add(self.a1)
        self.client.logout()
        resp = self.client.get(reverse("book-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        resp2 = self.client.get(reverse("book-detail", args=[b.id]))
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["title"], "B1")
        self.assertEqual(resp2.data["genre"], "X")

    def test_update_and_delete_book(self):
        b = Book.objects.create(title="Old", genre="G", description="D", available=True)
        b.authors.add(self.a1)
        url = reverse("book-detail", args=[b.id])
        data = {
            "title": "New",
            "genre": "NewG",
            "description": "Desc2",
            "available": False,
            "author_ids": [self.a2.id],
        }
        resp = self.client.put(url, data, format="json")
        self.assertEqual(resp.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.title, "New")
        self.assertFalse(b.available)
        self.assertEqual(list(b.authors.all()), [self.a2])
        # delete
        resp2 = self.client.delete(url)
        self.assertEqual(resp2.status_code, 204)
        self.assertFalse(Book.objects.filter(id=b.id).exists())

    def test_filter_search_ordering(self):
        # создаём 5 книг
        for i in range(5):
            bk = Book.objects.create(
                title=f"Book{i}",
                genre="X" if i % 2 == 0 else "Y",
                description="",
                available=(i % 2 == 0),
            )
            bk.authors.add(self.a1 if i % 2 else self.a2)
        # filter by genre
        resp = self.client.get(reverse("book-list") + "?genre=X")
        for it in resp.data["results"]:
            self.assertEqual(it["genre"], "X")
        # filter by available
        resp2 = self.client.get(reverse("book-list") + "?available=False")
        for it in resp2.data["results"]:
            self.assertFalse(it["available"])
        # filter by author
        resp3 = self.client.get(reverse("book-list") + f"?authors={self.a1.id}")
        for it in resp3.data["results"]:
            self.assertIn(self.a1.id, it["authors"])
        # search title
        resp4 = self.client.get(reverse("book-list") + "?search=Book1")
        self.assertTrue(all("Book1" in it["title"] for it in resp4.data["results"]))
        # search genre
        resp5 = self.client.get(reverse("book-list") + "?search=Y")
        self.assertTrue(all(it["genre"] == "Y" for it in resp5.data["results"]))
        # ordering by title desc
        resp6 = self.client.get(reverse("book-list") + "?ordering=-title")
        titles = [it["title"] for it in resp6.data["results"]]
        self.assertEqual(titles, sorted(titles, reverse=True))


class LoanTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        # одна книга
        self.book = Book.objects.create(
            title="LoanMe", genre="G", description="", available=True
        )
        self.book.authors.add(Author.objects.create(name="Au"))

    def test_create_and_book_unavailability(self):
        url = reverse("loan-list")
        resp = self.client.post(url, {"book": self.book.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        loan = Loan.objects.first()
        self.assertEqual(loan.user, self.admin)
        self.book.refresh_from_db()
        self.assertFalse(self.book.available)
        # попробовать взять ещё раз — упадёт
        resp2 = self.client.post(url, {"book": self.book.id}, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_retrieve_and_return(self):
        loan = Loan.objects.create(user=self.admin, book=self.book)
        # вручную сделать unavailable
        self.book.available = False
        self.book.save()
        # list
        resp = self.client.get(reverse("loan-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        # retrieve
        resp2 = self.client.get(reverse("loan-detail", args=[loan.id]))
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["id"], loan.id)
        self.assertEqual(resp2.data["status"], "на руках")
        # return via custom action
        ret_url = reverse("loan-return-book", args=[loan.id])
        resp3 = self.client.post(ret_url)
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.data.get("status"), "Возвращена")
        loan.refresh_from_db()
        self.assertIsNotNone(loan.return_date)
        self.book.refresh_from_db()
        self.assertTrue(self.book.available)

    def test_regular_user_sees_only_their_loans(self):
        # создаём чужой займ
        other_loan = Loan.objects.create(user=self.admin, book=self.book)
        # у другой книги
        book2 = Book.objects.create(
            title="B2", genre="", description="", available=True
        )
        book2.authors.add(self.book.authors.first())
        my_loan = Loan.objects.create(user=self.user, book=book2)
        # тест под admin
        resp_admin = self.client.get(reverse("loan-list"))
        self.assertEqual(resp_admin.data["count"], 2)
        # тест под обычным
        self.client.logout()
        assert self.client.login(username="user", password="pass2")
        resp_user = self.client.get(reverse("loan-list"))
        self.assertEqual(resp_user.data["count"], 1)
        self.assertEqual(resp_user.data["results"][0]["user"], self.user.id)

    def test_search_and_ordering_loans(self):
        # два займа с разным временем
        l1 = Loan.objects.create(user=self.user, book=self.book)
        # подлатать дату
        l1.borrowed_at = datetime.now() - timedelta(days=1)
        l1.save()
        book3 = Book.objects.create(
            title="ZZZ", genre="", description="", available=True
        )
        book3.authors.add(self.book.authors.first())
        l2 = Loan.objects.create(user=self.user, book=book3)
        # search по названию книги
        resp = self.client.get(reverse("loan-list") + "?search=ZZZ")
        self.assertEqual(resp.data["count"], 1)
        # ordering по borrowed_at asc
        resp2 = self.client.get(reverse("loan-list") + "?ordering=loan_date")
        dates = [it["loan_date"] for it in resp2.data["results"]]
        self.assertEqual(dates, sorted(dates))
