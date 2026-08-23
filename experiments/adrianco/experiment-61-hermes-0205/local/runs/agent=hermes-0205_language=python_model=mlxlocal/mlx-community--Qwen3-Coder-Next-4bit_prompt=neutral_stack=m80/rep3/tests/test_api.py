#!/usr/bin/env python3
"""Integration tests for Book API REST service."""

import json
import os
import unittest
import tempfile
from app import app, DATABASE, init_db


class BookAPITestCase(unittest.TestCase):
    """Test cases for Book API."""

    def setUp(self):
        """Set up test client and test database."""
        self.app = app.test_client()
        self.app.testing = True
        
        # Use a temporary database file for testing
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # Override DATABASE for testing
        import app as app_module
        app_module.DATABASE = self.db_path
        
        # Initialize database within app context
        with app.app_context():
            init_db()
    
    def tearDown(self):
        """Clean up after tests."""
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    def test_health_check(self):
        """Test health check endpoint."""
        with app.app_context():
            response = self.app.get('/health')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['status'], 'healthy')
    
    def test_list_books_empty(self):
        """Test listing books when database is empty."""
        with app.app_context():
            response = self.app.get('/books')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['count'], 0)
            self.assertEqual(data['books'], [])
    
    def test_create_book(self):
        """Test creating a new book."""
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        with app.app_context():
            response = self.app.post('/books', 
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['title'], book_data['title'])
            self.assertEqual(data['author'], book_data['author'])
            self.assertEqual(data['year'], book_data['year'])
            self.assertEqual(data['isbn'], book_data['isbn'])
            self.assertIn('id', data)
            self.assertIsNotNone(data['id'])
            self.assertIn('created_at', data)
    
    def test_create_book_missing_title(self):
        """Test creating a book without title (should fail)."""
        book_data = {
            'author': 'Some Author',
            'year': 2023
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertIn('errors', data)
            self.assertIn('title is required', data['errors'])
    
    def test_create_book_missing_author(self):
        """Test creating a book without author (should fail)."""
        book_data = {
            'title': 'Some Book',
            'year': 2023
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertIn('errors', data)
            self.assertIn('author is required', data['errors'])
    
    def test_create_book_empty_title(self):
        """Test creating a book with empty title (should fail)."""
        book_data = {
            'title': '',
            'author': 'Some Author'
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 400)
    
    def test_create_book_empty_author(self):
        """Test creating a book with empty author (should fail)."""
        book_data = {
            'title': 'Some Book',
            'author': ''
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 400)
    
    def test_get_book_not_found(self):
        """Test getting a non-existent book."""
        with app.app_context():
            response = self.app.get('/books/9999')
            self.assertEqual(response.status_code, 404)
            data = json.loads(response.data)
            self.assertIn('error', data)
            self.assertEqual(data['error'], 'Book not found')
    
    def test_update_book(self):
        """Test updating a book."""
        # First create a book
        book_data = {
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2020
        }
        with app.app_context():
            create_response = self.app.post('/books',
                                             data=json.dumps(book_data),
                                             content_type='application/json')
            self.assertEqual(create_response.status_code, 201)
            data = json.loads(create_response.data)
            book_id = data['id']
            
            # Now update it
            update_data = {
                'title': 'Updated Title',
                'year': 2021
            }
            update_response = self.app.put(f'/books/{book_id}',
                                            data=json.dumps(update_data),
                                            content_type='application/json')
            self.assertEqual(update_response.status_code, 200)
            updated_data = json.loads(update_response.data)
            self.assertEqual(updated_data['title'], 'Updated Title')
            self.assertEqual(updated_data['author'], 'Original Author')  # Unchanged
            self.assertEqual(updated_data['year'], 2021)
    
    def test_update_book_not_found(self):
        """Test updating a non-existent book."""
        update_data = {
            'title': 'New Title'
        }
        with app.app_context():
            response = self.app.put('/books/9999',
                                     data=json.dumps(update_data),
                                     content_type='application/json')
            self.assertEqual(response.status_code, 404)
    
    def test_delete_book(self):
        """Test deleting a book."""
        # First create a book
        book_data = {
            'title': 'To Be Deleted',
            'author': 'Delete Me'
        }
        with app.app_context():
            create_response = self.app.post('/books',
                                             data=json.dumps(book_data),
                                             content_type='application/json')
            self.assertEqual(create_response.status_code, 201)
            data = json.loads(create_response.data)
            book_id = data['id']
            
            # Now delete it
            delete_response = self.app.delete(f'/books/{book_id}')
            self.assertEqual(delete_response.status_code, 200)
            data = json.loads(delete_response.data)
            self.assertIn('message', data)
            self.assertEqual(data['message'], 'Book deleted successfully')
            
            # Verify it's gone
            get_response = self.app.get(f'/books/{book_id}')
            self.assertEqual(get_response.status_code, 404)
    
    def test_delete_book_not_found(self):
        """Test deleting a non-existent book."""
        with app.app_context():
            response = self.app.delete('/books/9999')
            self.assertEqual(response.status_code, 404)
    
    def test_list_books_with_filter(self):
        """Test listing books with author filter."""
        # Create multiple books
        books = [
            {'title': 'Book 1', 'author': 'Author A', 'year': 2020},
            {'title': 'Book 2', 'author': 'Author B', 'year': 2021},
            {'title': 'Book 3', 'author': 'Author A', 'year': 2022}
        ]
        
        with app.app_context():
            for book in books:
                self.app.post('/books',
                             data=json.dumps(book),
                             content_type='application/json')
            
            # Filter by author
            response = self.app.get('/books?author=Author A')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data['count'], 2)
            for book in data['books']:
                self.assertEqual(book['author'], 'Author A')
    
    def test_create_book_with_year_string(self):
        """Test creating a book with year as string (should convert)."""
        book_data = {
            'title': 'Book with Year',
            'author': 'Author Name',
            'year': '1999'
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 201)
            data = json.loads(response.data)
            self.assertEqual(data['year'], 1999)
    
    def test_create_book_with_invalid_year(self):
        """Test creating a book with invalid year."""
        book_data = {
            'title': 'Book with Bad Year',
            'author': 'Author Name',
            'year': -1
        }
        with app.app_context():
            response = self.app.post('/books',
                                      data=json.dumps(book_data),
                                      content_type='application/json')
            self.assertEqual(response.status_code, 400)
    
    def test_update_book_with_invalid_year(self):
        """Test updating a book with invalid year."""
        # First create a book
        book_data = {
            'title': 'Original',
            'author': 'Author'
        }
        with app.app_context():
            create_response = self.app.post('/books',
                                             data=json.dumps(book_data),
                                             content_type='application/json')
            self.assertEqual(create_response.status_code, 201)
            data = json.loads(create_response.data)
            book_id = data['id']
            
            # Try to update with invalid year
            update_data = {'year': 10000}
            response = self.app.put(f'/books/{book_id}',
                                     data=json.dumps(update_data),
                                     content_type='application/json')
            self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
