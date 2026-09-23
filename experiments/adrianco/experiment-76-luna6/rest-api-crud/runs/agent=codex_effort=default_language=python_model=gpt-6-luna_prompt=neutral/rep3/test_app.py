import sqlite3
import tempfile
import unittest

from app import initialize_database, make_handler


class BookApiUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = self.temp_dir.name + "/books.sqlite3"
        initialize_database(self.database)
        self.handler = make_handler(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_database_schema_supports_book_creation_and_listing(self):
        with sqlite3.connect(self.database) as connection:
            cursor = connection.execute(
                "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
                ("Dune", "Frank Herbert", 1965, "123"),
            )
            row = connection.execute("SELECT title, author FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
        self.assertEqual(row, ("Dune", "Frank Herbert"))

    def test_book_input_validation_requires_title_and_author(self):
        validate = self.handler._validate
        with self.assertRaisesRegex(ValueError, "title is required"):
            validate({"author": "Frank Herbert"})
        with self.assertRaisesRegex(ValueError, "author is required"):
            validate({"title": "Dune", "author": " "})
        self.assertEqual(validate({"title": " Dune ", "author": "Frank Herbert"}),
                         ("Dune", "Frank Herbert", None, None))

    def test_optional_field_types_are_validated(self):
        with self.assertRaisesRegex(ValueError, "year must be an integer"):
            self.handler._validate({"title": "Dune", "author": "Frank Herbert", "year": "1965"})
        with self.assertRaisesRegex(ValueError, "isbn must be a string"):
            self.handler._validate({"title": "Dune", "author": "Frank Herbert", "isbn": 123})


if __name__ == "__main__":
    unittest.main()
