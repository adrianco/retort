import unittest
import json
import os
import sys
import tempfile

# Ensure app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app


class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test client and a temporary database for each test."""
        app.DATABASE = tempfile.mktemp(suffix='.db')
        app.init_db()
        self.client = app.app.test_client()

    def tearDown(self):
        """Clean up the temporary database after each test."""
        self.client = None
        if os.path.exists(app.DATABASE):
            os.remove(app.DATABASE)

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')

    def test_create_book(self):
        """Test creating a new book."""
        response = self.client.post(
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
        self.assertIsNotNone(data['id'])

    def test_create_book_missing_title(self):
        """Test creating a book without a title returns 400."""
        response = self.client.post(
            '/books',
            data=json.dumps({'author': 'Someone'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Title is required')

    def test_create_book_missing_author(self):
        """Test creating a book without an author returns 400."""
        response = self.client.post(
            '/books',
            data=json.dumps({'title': 'Some Book'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Author is required')

    def test_list_books(self):
        """Test listing all books."""
        # Create a couple of books
        self.client.post('/books', data=json.dumps({
            'title': '1984', 'author': 'George Orwell', 'year': 1949
        }), content_type='application/json')
        self.client.post('/books', data=json.dumps({
            'title': 'Animal Farm', 'author': 'George Orwell', 'year': 1945
        }), content_type='application/json')

        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)

    def test_list_books_filter_by_author(self):
        """Test listing books filtered by author."""
        self.client.post('/books', data=json.dumps({
            'title': '1984', 'author': 'George Orwell', 'year': 1949
        }), content_type='application/json')
        self.client.post('/books', data=json.dumps({
            'title': 'Dune', 'author': 'Frank Herbert', 'year': 1965
        }), content_type='application/json')

        response = self.client.get('/books?author=George+Orwell')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], '1984')

    def test_get_book(self):
        """Test getting a single book by ID."""
        response = self.client.post('/books', data=json.dumps({
            'title': 'Brave New World', 'author': 'Aldous Huxley', 'year': 1932
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = self.client.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Brave New World')
        self.assertEqual(data['id'], book_id)

    def test_get_book_not_found(self):
        """Test getting a non-existent book returns 404."""
        response = self.client.get('/books/9999')
        self.assertEqual(response.status_code, 404)

    def test_update_book(self):
        """Test updating a book."""
        response = self.client.post('/books', data=json.dumps({
            'title': 'Original Title', 'author': 'Original Author'
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = self.client.put(
            f'/books/{book_id}',
            data=json.dumps({'title': 'Updated Title', 'author': 'New Author'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Title')
        self.assertEqual(data['author'], 'New Author')

    def test_delete_book(self):
        """Test deleting a book."""
        response = self.client.post('/books', data=json.dumps({
            'title': 'To Delete', 'author': 'Someone'
        }), content_type='application/json')
        book_id = json.loads(response.data)['id']

        response = self.client.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 204)

        # Verify it's gone
        response = self.client.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
