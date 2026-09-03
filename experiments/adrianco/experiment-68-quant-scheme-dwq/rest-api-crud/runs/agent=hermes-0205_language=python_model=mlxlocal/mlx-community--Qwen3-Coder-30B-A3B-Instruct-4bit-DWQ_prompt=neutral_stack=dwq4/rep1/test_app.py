import unittest
import json
import os
import sys
import sqlite3
from app import app, init_db

# Add the project directory to the path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        # Set up test database
        self.app = app.test_client()
        # Initialize database with test data
        init_db()
        
        # Clear any existing data to ensure clean tests
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM books')
        conn.commit()
        conn.close()

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
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '123-456-789'
        }
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')
        self.assertEqual(data['year'], 2023)
        self.assertEqual(data['isbn'], '123-456-789')
        self.assertIn('id', data)

    def test_create_book_missing_required_fields(self):
        """Test creating book with missing required fields"""
        # Test with missing title
        book_data = {
            'author': 'Test Author',
            'year': 2023
        }
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
        # Test with missing author
        book_data = {
            'title': 'Test Book',
            'year': 2023
        }
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get_all_books(self):
        """Test getting all books"""
        # Create a test book first
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
        }
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book')

    def test_get_books_by_author(self):
        """Test getting books filtered by author"""
        # Create test books
        book1 = {
            'title': 'Book 1',
            'author': 'Author A',
            'year': 2020
        }
        book2 = {
            'title': 'Book 2',
            'author': 'Author B',
            'year': 2021
        }
        book3 = {
            'title': 'Book 3',
            'author': 'Author A',
            'year': 2022
        }
        
        self.app.post('/books', data=json.dumps(book1), content_type='application/json')
        self.app.post('/books', data=json.dumps(book2), content_type='application/json')
        self.app.post('/books', data=json.dumps(book3), content_type='application/json')
        
        # Get books by author A
        response = self.app.get('/books?author=Author A')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'Author A')

    def test_get_single_book(self):
        """Test getting a single book by ID"""
        # Create a test book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
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
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')

    def test_get_nonexistent_book(self):
        """Test getting a non-existent book"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)

    def test_update_book(self):
        """Test updating a book"""
        # Create a test book
        book_data = {
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2020
        }
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        # Update the book
        update_data = {
            'title': 'Updated Title',
            'author': 'Updated Author',
            'year': 2021,
            'isbn': '999-888-777'
        }
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Title')
        self.assertEqual(data['author'], 'Updated Author')
        self.assertEqual(data['year'], 2021)
        self.assertEqual(data['isbn'], '999-888-777')

    def test_update_nonexistent_book(self):
        """Test updating a non-existent book"""
        update_data = {
            'title': 'Updated Title',
            'author': 'Updated Author'
        }
        response = self.app.put('/books/999',
                               data=json.dumps(update_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_delete_book(self):
        """Test deleting a book"""
        # Create a test book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
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
        
        # Verify the book is deleted
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

    def test_delete_nonexistent_book(self):
        """Test deleting a non-existent book"""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()