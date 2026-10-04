import tempfile
import unittest
from pathlib import Path

from app import connect, create_handler


class BooksApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp.name) / "test.db")
        self.handler = create_handler(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_required_fields_and_optional_field_validation(self):
        with self.assertRaisesRegex(ValueError, "title is required"):
            self.handler.normalize({"author": "Ada"})
        with self.assertRaisesRegex(ValueError, "author is required"):
            self.handler.normalize({"title": "Book"})
        with self.assertRaisesRegex(ValueError, "year must be an integer"):
            self.handler.normalize({"title": "Book", "author": "Ada", "year": True})
        self.assertEqual(self.handler.normalize({"title": " Book ", "author": " Ada "}), ("Book", "Ada", None, None))

    def test_sqlite_create_filter_update_and_delete(self):
        with connect(self.db_path) as db:
            cursor = db.execute("INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)", self.handler.normalize({"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"}))
            book_id = cursor.lastrowid
            books = db.execute("SELECT * FROM books WHERE author LIKE ? COLLATE NOCASE", ("%herbert%",)).fetchall()
            self.assertEqual(len(books), 1)
            self.assertEqual(books[0]["title"], "Dune")
            db.execute("UPDATE books SET title=? WHERE id=?", ("Dune Messiah", book_id))
            self.assertEqual(db.execute("SELECT title FROM books WHERE id=?", (book_id,)).fetchone()[0], "Dune Messiah")
            db.execute("DELETE FROM books WHERE id=?", (book_id,))
            self.assertIsNone(db.execute("SELECT id FROM books WHERE id=?", (book_id,)).fetchone())

    def test_book_id_route_parsing(self):
        self.assertEqual(self.handler.book_id("/books/42"), 42)
        self.assertIsNone(self.handler.book_id("/books/nope"))
        self.assertIsNone(self.handler.book_id("/other/42"))


if __name__ == "__main__":
    unittest.main()
