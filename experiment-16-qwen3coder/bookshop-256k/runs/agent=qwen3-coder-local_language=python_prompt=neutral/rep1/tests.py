import unittest
import json
import os
import sys

# Add the current directory to Python path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        # Set up test client
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize database
        init_db()
        
        # Create test data
        self.book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        # Create a book for testing
        response = self.app.post('/books', 
                               data=json.dumps(self.book_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.book = json.loads(response.data)
        self.book_id = self.book['id']

    def tearDown(self):
        self.app_context.pop()
        # Clean up database file
        if os.path.exists('books.db'):
            os.remove('books.db')

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book"""
        new_book = {
            'title': 'Another Book',
            'author': 'Another Author',
            'year': 2022,
            'isbn': '0987654321'
        }
        
        response = self.app.post('/books',
                               data=json.dumps(new_book),
                               content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        self.assertEqual(data['title'], new_book['title'])
        self.assertEqual(data['author'], new_book['author'])
        self.assertEqual(data['year'], new_book['year'])
        self.assertEqual(data['isbn'], new_book['isbn'])
        self.assertIn('id', data)

    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields"""
        # Missing title
        book_data = {
            'author': 'Test Author',
            'year': 2023
        }
        
        response = self.app.post('/books',
                               data=json.dumps(book_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Missing author
        book_data = {
            'title': 'Test Book',
            'year': 2023
        }
        
        response = self.app.post('/books',
                               data=json.dumps(book_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get_books(self):
        """Test getting all books"""
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_get_books_by_author(self):
        """Test getting books filtered by author"""
        response = self.app.get('/books?author=Test Author')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertIsInstance(data, list)
        # All books should have 'Test Author' in their author field
        for book in data:
            self.assertIn('Test Author', book['author'])

    def test_get_book_by_id(self):
        """Test getting a single book by ID"""
        response = self.app.get(f'/books/{self.book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['id'], self.book_id)
        self.assertEqual(data['title'], self.book_data['title'])
        self.assertEqual(data['author'], self.book_data['author'])
        self.assertEqual(data['year'], self.book_data['year'])
        self.assertEqual(data['isbn'], self.book_data['isbn'])

    def test_get_nonexistent_book(self):
        """Test getting a non-existent book"""
        response = self.app.get('/books/99999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')

    def test_update_book(self):
        """Test updating a book"""
        updated_data = {
            'title': 'Updated Book Title',
            'author': 'Updated Author',
            'year': 2024,
            'isbn': '1111111111'
        }
        
        response = self.app.put(f'/books/{self.book_id}',
                              data=json.dumps(updated_data),
                              content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['id'], self.book_id)
        self.assertEqual(data['title'], updated_data['title'])
        self.assertEqual(data['author'], updated_data['author'])
        self.assertEqual(data['year'], updated_data['year'])
        self.assertEqual(data['isbn'], updated_data['isbn'])

    def test_update_nonexistent_book(self):
        """Test updating a non-existent book"""
        updated_data = {
            'title': 'Updated Book Title',
            'author': 'Updated Author'
        }
        
        response = self.app.put('/books/99999',
                              data=json.dumps(updated_data),
                              content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')

    def test_delete_book(self):
        """Test deleting a book"""
        response = self.app.delete(f'/books/{self.book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')

    def test_delete_nonexistent_book(self):
        """Test deleting a non-existent book"""
        response = self.app.delete('/books/99999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')

    def test_unique_isbn_constraint(self):
        """Test that ISBN must be unique"""
        # Create a book with the same ISBN as existing
        book_data = {
            'title': 'Another Book',
            'author': 'Another Author',
            'isbn': '1234567890'  # Same ISBN as existing
        }
        
        response = self.app.post('/books',
                               data=json.dumps(book_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()