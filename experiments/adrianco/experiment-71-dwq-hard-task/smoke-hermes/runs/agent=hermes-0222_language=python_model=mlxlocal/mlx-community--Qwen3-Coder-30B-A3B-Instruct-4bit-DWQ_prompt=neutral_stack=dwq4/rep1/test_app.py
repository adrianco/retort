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
        
        # Clear any existing data
        with app.app_context():
            import sqlite3
            conn = sqlite3.connect('books.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM books')
            conn.commit()
            conn.close()

    def tearDown(self):
        """Tear down after tests"""
        self.app_context.pop()
        
        # Remove test database file
        if os.path.exists('books.db'):
            os.remove('books.db')

    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.app.get('/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book"""
        response = self.app.post('/books',
                                data=json.dumps({
                                    'title': '1984',
                                    'author': 'George Orwell',
                                    'year': 1948,
                                    'isbn': '978-0-452-28423-4'
                                }),
                                content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0-452-28423-4')

    def test_get_books(self):
        """Test getting all books"""
        # First create a book
        self.app.post('/books',
                     data=json.dumps({
                         'title': '1984',
                         'author': 'George Orwell',
                         'year': 1948,
                         'isbn': '978-0-452-28423-4'
                     }),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], '1984')
        self.assertEqual(data[0]['author'], 'George Orwell')

    def test_get_book_by_id(self):
        """Test getting a book by ID"""
        # First create a book
        response = self.app.post('/books',
                                data=json.dumps({
                                    'title': '1984',
                                    'author': 'George Orwell',
                                    'year': 1948,
                                    'isbn': '978-0-452-28423-4'
                                }),
                                content_type='application/json')
        
        book_data = json.loads(response.data)
        book_id = book_data['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['id'], book_id)

    def test_update_book(self):
        """Test updating a book"""
        # First create a book
        response = self.app.post('/books',
                                data=json.dumps({
                                    'title': '1984',
                                    'author': 'George Orwell',
                                    'year': 1948,
                                    'isbn': '978-0-452-28423-4'
                                }),
                                content_type='application/json')
        
        book_data = json.loads(response.data)
        book_id = book_data['id']
        
        # Update the book
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps({
                                   'title': 'Nineteen Eighty-Four',
                                   'author': 'George Orwell',
                                   'year': 1948,
                                   'isbn': '978-0-452-28423-4'
                               }),
                               content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], 'Nineteen Eighty-Four')
        self.assertEqual(data['author'], 'George Orwell')

    def test_delete_book(self):
        """Test deleting a book"""
        # First create a book
        response = self.app.post('/books',
                                data=json.dumps({
                                    'title': '1984',
                                    'author': 'George Orwell',
                                    'year': 1948,
                                    'isbn': '978-0-452-28423-4'
                                }),
                                content_type='application/json')
        
        book_data = json.loads(response.data)
        book_id = book_data['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], 'Book deleted successfully')
        
        # Verify it's deleted by trying to get it
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

    def test_filter_books_by_author(self):
        """Test filtering books by author"""
        # Create multiple books
        self.app.post('/books',
                     data=json.dumps({
                         'title': '1984',
                         'author': 'George Orwell',
                         'year': 1948,
                         'isbn': '978-0-452-28423-4'
                     }),
                     content_type='application/json')
        
        self.app.post('/books',
                     data=json.dumps({
                         'title': 'Animal Farm',
                         'author': 'George Orwell',
                         'year': 1945,
                         'isbn': '978-0-452-28423-5'
                     }),
                     content_type='application/json')
        
        self.app.post('/books',
                     data=json.dumps({
                         'title': 'To Kill a Mockingbird',
                         'author': 'Harper Lee',
                         'year': 1960,
                         'isbn': '978-0-06-112008-4'
                     }),
                     content_type='application/json')
        
        # Filter by author
        response = self.app.get('/books?author=Orwell')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'George Orwell')

    def test_create_book_missing_required_fields(self):
        """Test creating a book with missing required fields"""
        response = self.app.post('/books',
                                data=json.dumps({
                                    'title': '1984'
                                    # Missing author
                                }),
                                content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Title and author are required')

    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], 'Book not found')

if __name__ == '__main__':
    unittest.main()