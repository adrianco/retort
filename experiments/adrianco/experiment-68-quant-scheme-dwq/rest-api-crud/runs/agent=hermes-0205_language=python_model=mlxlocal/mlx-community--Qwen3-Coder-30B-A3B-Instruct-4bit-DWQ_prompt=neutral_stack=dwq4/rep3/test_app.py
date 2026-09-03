import unittest
import json
import os
import sys
from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database before each test."""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        init_db()
        
    def tearDown(self):
        """Clean up after each test."""
        self.app_context.pop()
        # Remove the database file after tests
        if os.path.exists('books.db'):
            os.remove('books.db')

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book."""
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
        self.assertIn('id', data)

    def test_get_all_books(self):
        """Test getting all books."""
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
        """Test getting a book by ID."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        create_data = json.loads(create_response.data)
        book_id = create_data['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')

    def test_update_book(self):
        """Test updating a book."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        create_data = json.loads(create_response.data)
        book_id = create_data['id']
        
        # Update the book
        update_data = {
            'title': 'Updated Test Book',
            'author': 'Updated Test Author',
            'year': 2024,
            'isbn': '0987654321'
        }
        
        response = self.app.put(f'/books/{book_id}',
                              data=json.dumps(update_data),
                              content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Test Book')
        self.assertEqual(data['author'], 'Updated Test Author')
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['isbn'], '0987654321')

    def test_delete_book(self):
        """Test deleting a book."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023,
            'isbn': '1234567890'
        }
        
        create_response = self.app.post('/books', 
                                       data=json.dumps(book_data),
                                       content_type='application/json')
        create_data = json.loads(create_response.data)
        book_id = create_data['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')
        
        # Verify the book is deleted
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

    def test_filter_books_by_author(self):
        """Test filtering books by author."""
        # Create two books with different authors
        book1_data = {
            'title': 'Book 1',
            'author': 'Author A',
            'year': 2020,
            'isbn': '1111111111'
        }
        
        book2_data = {
            'title': 'Book 2',
            'author': 'Author B',
            'year': 2021,
            'isbn': '2222222222'
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

    def test_create_book_missing_required_fields(self):
        """Test creating a book with missing required fields."""
        book_data = {
            'title': 'Test Book'
            # Missing author
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Title and author are required')

if __name__ == '__main__':
    unittest.main()