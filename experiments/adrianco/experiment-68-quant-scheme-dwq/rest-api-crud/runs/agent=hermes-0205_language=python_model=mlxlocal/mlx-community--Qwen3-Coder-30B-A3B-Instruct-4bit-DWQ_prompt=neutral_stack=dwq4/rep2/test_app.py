import unittest
import json
import os
import sys

# Add the project directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        init_db()
        
        # Clear the database before each test
        with app.app_context():
            conn = app.config['db'] if 'db' in app.config else None
            if not conn:
                import sqlite3
                conn = sqlite3.connect('books.db')
                conn.row_factory = sqlite3.Row
            conn.execute('DELETE FROM books')
            conn.commit()
            conn.close()

    def tearDown(self):
        """Tear down after each test"""
        self.app_context.pop()

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book"""
        # Test with valid data
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0-7432-7356-5'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'The Great Gatsby')
        self.assertEqual(data['author'], 'F. Scott Fitzgerald')
        self.assertEqual(data['year'], 1925)
        self.assertEqual(data['isbn'], '978-0-7432-7356-5')
        self.assertIn('id', data)

    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields"""
        # Test with missing title
        book_data = {
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_get_all_books(self):
        """Test getting all books"""
        # Create a book first
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'The Great Gatsby')
        self.assertEqual(data[0]['author'], 'F. Scott Fitzgerald')
        self.assertEqual(data[0]['year'], 1925)

    def test_get_book_by_id(self):
        """Test getting a single book by ID"""
        # Create a book first
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['title'], 'The Great Gatsby')
        self.assertEqual(data['author'], 'F. Scott Fitzgerald')
        self.assertEqual(data['year'], 1925)

    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_update_book(self):
        """Test updating a book"""
        # Create a book first
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        # Update the book
        updated_data = {
            'title': 'The Great Gatsby - Updated',
            'author': 'F. Scott Fitzgerald',
            'year': 1926,
            'isbn': '978-0-7432-7356-6'
        }
        
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(data['title'], 'The Great Gatsby - Updated')
        self.assertEqual(data['author'], 'F. Scott Fitzgerald')
        self.assertEqual(data['year'], 1926)
        self.assertEqual(data['isbn'], '978-0-7432-7356-6')

    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist"""
        updated_data = {
            'title': 'The Great Gatsby - Updated',
            'author': 'F. Scott Fitzgerald',
            'year': 1926
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_delete_book(self):
        """Test deleting a book"""
        # Create a book first
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')

        # Verify it's deleted by trying to get it
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

    def test_filter_books_by_author(self):
        """Test filtering books by author"""
        # Create multiple books
        book1_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925
        }
        
        book2_data = {
            'title': 'Tender is the Night',
            'author': 'F. Scott Fitzgerald',
            'year': 1934
        }
        
        book3_data = {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'year': 1960
        }
        
        self.app.post('/books', 
                     data=json.dumps(book1_data),
                     content_type='application/json')
        
        self.app.post('/books', 
                     data=json.dumps(book2_data),
                     content_type='application/json')
        
        self.app.post('/books', 
                     data=json.dumps(book3_data),
                     content_type='application/json')
        
        # Filter by author
        response = self.app.get('/books?author=F. Scott Fitzgerald')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'F. Scott Fitzgerald')

if __name__ == '__main__':
    unittest.main()