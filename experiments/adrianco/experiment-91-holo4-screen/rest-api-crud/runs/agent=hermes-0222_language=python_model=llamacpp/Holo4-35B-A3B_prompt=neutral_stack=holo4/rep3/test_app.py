import unittest
import os
import json
import tempfile
import app as myapp


class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and fresh database before each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        myapp.DATABASE = self.db_path
        self.app = myapp.app.test_client()
        self.app.testing = True
        myapp.init_db()

    def tearDown(self):
        """Clean up after each test."""
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')

    def test_create_book(self):
        """Test creating a new book."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'title': 'The Great Gatsby',
                'author': 'F. Scott Fitzgerald',
                'year': 1925,
                'isbn': '978-0743273565'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'The Great Gatsby')
        self.assertEqual(data['author'], 'F. Scott Fitzgerald')
        self.assertEqual(data['year'], 1925)
        self.assertEqual(data['isbn'], '978-0743273565')
        self.assertIn('id', data)

    def test_create_book_missing_title(self):
        """Test creating a book without title returns 400."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'author': 'F. Scott Fitzgerald',
                'year': 1925
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_create_book_missing_author(self):
        """Test creating a book without author returns 400."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'title': 'The Great Gatsby',
                'year': 1925
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_list_books(self):
        """Test listing all books."""
        # Create a book first
        self.app.post(
            '/books',
            data=json.dumps({
                'title': '1984',
                'author': 'George Orwell',
                'year': 1949
            }),
            content_type='application/json'
        )
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], '1984')

    def test_list_books_filter_by_author(self):
        """Test filtering books by author."""
        self.app.post(
            '/books',
            data=json.dumps({
                'title': '1984',
                'author': 'George Orwell',
                'year': 1949
            }),
            content_type='application/json'
        )
        self.app.post(
            '/books',
            data=json.dumps({
                'title': 'Animal Farm',
                'author': 'George Orwell',
                'year': 1945
            }),
            content_type='application/json'
        )
        self.app.post(
            '/books',
            data=json.dumps({
                'title': 'Brave New World',
                'author': 'Aldous Huxley',
                'year': 1932
            }),
            content_type='application/json'
        )
        response = self.app.get('/books?author=George Orwell')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'George Orwell')

    def test_get_book(self):
        """Test getting a single book by ID."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'title': 'Dune',
                'author': 'Frank Herbert',
                'year': 1965
            }),
            content_type='application/json'
        )
        book_id = json.loads(response.data)['id']
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Dune')

    def test_get_book_not_found(self):
        """Test getting a non-existent book returns 404."""
        response = self.app.get('/books/9999')
        self.assertEqual(response.status_code, 404)

    def test_update_book(self):
        """Test updating a book."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'title': 'The Hobbit',
                'author': 'J.R.R. Tolkien',
                'year': 1937
            }),
            content_type='application/json'
        )
        book_id = json.loads(response.data)['id']
        response = self.app.put(
            f'/books/{book_id}',
            data=json.dumps({
                'title': 'The Hobbit (Updated)',
                'year': 1937
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'The Hobbit (Updated)')

    def test_delete_book(self):
        """Test deleting a book."""
        response = self.app.post(
            '/books',
            data=json.dumps({
                'title': 'Fahrenheit 451',
                'author': 'Ray Bradbury',
                'year': 1953
            }),
            content_type='application/json'
        )
        book_id = json.loads(response.data)['id']
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        # Verify it's gone
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
