import unittest
import json
import os
import sys
import sqlite3

# Add the current directory to Python path so we can import app
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
        conn = sqlite3.connect('books.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM books')
        conn.commit()
        conn.close()
        
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
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')
        self.assertEqual(data['year'], 2023)
        self.assertEqual(data['isbn'], '1234567890')
        
    def test_create_book_missing_required_fields(self):
        """Test creating a book with missing required fields"""
        book_data = {
            'title': 'Test Book'
            # Missing author field
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_get_books(self):
        """Test getting all books"""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book')
        
    def test_get_book_by_id(self):
        """Test getting a book by ID"""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        book_id = json.loads(response.data)['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')
        
    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_update_book(self):
        """Test updating a book"""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        book_id = json.loads(response.data)['id']
        
        # Update the book
        updated_data = {
            'title': 'Updated Book',
            'author': 'Updated Author',
            'year': 2024,
            'isbn': '0987654321'
        }
        
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Book')
        self.assertEqual(data['author'], 'Updated Author')
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['isbn'], '0987654321')
        
    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist"""
        updated_data = {
            'title': 'Updated Book',
            'author': 'Updated Author'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_delete_book(self):
        """Test deleting a book"""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        book_id = json.loads(response.data)['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        # Verify it's deleted by trying to get it
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)
        
    def test_delete_nonexistent_book(self):
        """Test deleting a book that doesn't exist"""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_filter_books_by_author(self):
        """Test filtering books by author"""
        # Create multiple books
        book1_data = {
            'title': 'Book 1',
            'author': 'Author A',
            'year': 2020
        }
        
        book2_data = {
            'title': 'Book 2',
            'author': 'Author B',
            'year': 2021
        }
        
        self.app.post('/books', 
                     data=json.dumps(book1_data),
                     content_type='application/json')
        
        self.app.post('/books', 
                     data=json.dumps(book2_data),
                     content_type='application/json')
        
        # Filter by author A
        response = self.app.get('/books?author=Author A')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['author'], 'Author A')
        
        # Filter by author B
        response = self.app.get('/books?author=Author B')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['author'], 'Author B')

if __name__ == '__main__':
    unittest.main()