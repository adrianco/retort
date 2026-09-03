#!/usr/bin/env python3
"""
Unit and integration tests for the Book API REST Service
"""

import unittest
import json
import os
import sys

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database."""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize database
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
        """Tear down test client."""
        self.app_context.pop()
        
        # Remove test database file
        if os.path.exists('books.db'):
            os.remove('books.db')

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a new book."""
        # Test valid book creation
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

    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields."""
        # Test with missing title
        book_data = {
            'author': 'Test Author'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_get_all_books(self):
        """Test getting all books."""
        # First create a book
        book_data = {
            'title': 'Test Book 1',
            'author': 'Test Author 1',
            'year': 2023
        }
        
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book 1')
        self.assertEqual(data[0]['author'], 'Test Author 1')
        self.assertEqual(data[0]['year'], 2023)

    def test_get_book_by_id(self):
        """Test getting a book by ID."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        # Get the created book by ID
        data = json.loads(response.data)
        book_id = data['id']
        
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        returned_data = json.loads(response.data)
        
        self.assertEqual(returned_data['title'], 'Test Book')
        self.assertEqual(returned_data['author'], 'Test Author')
        self.assertEqual(returned_data['year'], 2023)
        self.assertEqual(returned_data['id'], book_id)

    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist."""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_update_book(self):
        """Test updating a book."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author',
            'year': 2023
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        # Get the created book ID
        data = json.loads(response.data)
        book_id = data['id']
        
        # Update the book
        updated_data = {
            'title': 'Updated Test Book',
            'author': 'Updated Test Author',
            'year': 2024,
            'isbn': '0987654321'
        }
        
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        returned_data = json.loads(response.data)
        
        self.assertEqual(returned_data['title'], 'Updated Test Book')
        self.assertEqual(returned_data['author'], 'Updated Test Author')
        self.assertEqual(returned_data['year'], 2024)
        self.assertEqual(returned_data['isbn'], '0987654321')

    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist."""
        updated_data = {
            'title': 'Updated Test Book',
            'author': 'Updated Test Author'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_delete_book(self):
        """Test deleting a book."""
        # First create a book
        book_data = {
            'title': 'Test Book',
            'author': 'Test Author'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        # Get the created book ID
        data = json.loads(response.data)
        book_id = data['id']
        
        # Delete the book
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        # Verify it's deleted by trying to get it
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

    def test_delete_nonexistent_book(self):
        """Test deleting a book that doesn't exist."""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_filter_books_by_author(self):
        """Test filtering books by author."""
        # Create multiple books
        book1 = {
            'title': 'Book 1',
            'author': 'John Smith',
            'year': 2020
        }
        
        book2 = {
            'title': 'Book 2',
            'author': 'Jane Smith',
            'year': 2021
        }
        
        book3 = {
            'title': 'Book 3',
            'author': 'John Doe',
            'year': 2022
        }
        
        self.app.post('/books', 
                     data=json.dumps(book1),
                     content_type='application/json')
        
        self.app.post('/books', 
                     data=json.dumps(book2),
                     content_type='application/json')
        
        self.app.post('/books', 
                     data=json.dumps(book3),
                     content_type='application/json')
        
        # Filter by author containing "Smith"
        response = self.app.get('/books?author=Smith')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Should return 2 books (John Smith and Jane Smith)
        self.assertEqual(len(data), 2)
        
        # Verify the authors are correct
        authors = [book['author'] for book in data]
        self.assertIn('John Smith', authors)
        self.assertIn('Jane Smith', authors)

if __name__ == '__main__':
    unittest.main()