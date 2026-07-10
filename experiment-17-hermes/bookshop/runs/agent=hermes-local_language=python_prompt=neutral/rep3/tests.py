import unittest
import json
import os
import sys
import tempfile
import shutil

# Add the current directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize database (this should be clean each time)
        init_db()

    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book"""
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
        self.assertEqual(data['title'], book_data['title'])
        self.assertEqual(data['author'], book_data['author'])
        self.assertEqual(data['year'], book_data['year'])
        self.assertEqual(data['isbn'], book_data['isbn'])

    def test_get_all_books(self):
        """Test getting all books"""
        # First create a book
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0-7432-7356-5'
        }
        
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should have exactly 1 book now
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], book_data['title'])

    def test_get_book_by_id(self):
        """Test getting a book by ID"""
        # First create a book
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0-7432-7356-5'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        created_book = json.loads(create_response.data)
        book_id = created_book['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], book_data['title'])
        self.assertEqual(data['author'], book_data['author'])

    def test_update_book(self):
        """Test updating a book"""
        # First create a book
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0-7432-7356-5'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        created_book = json.loads(create_response.data)
        book_id = created_book['id']
        
        # Update the book
        update_data = {
            'title': 'The Great Gatsby - Updated',
            'author': 'F. Scott Fitzgerald',
            'year': 1926,
            'isbn': '978-0-7432-7356-6'
        }
        
        response = self.app.put(f'/books/{book_id}',
                              data=json.dumps(update_data),
                              content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], update_data['title'])
        self.assertEqual(data['year'], update_data['year'])

    def test_delete_book(self):
        """Test deleting a book"""
        # First create a book
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0-7432-7356-5'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        created_book = json.loads(create_response.data)
        book_id = created_book['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')

    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields"""
        book_data = {
            'title': 'The Great Gatsby'
            # Missing author
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

if __name__ == '__main__':
    unittest.main()
