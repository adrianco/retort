#!/usr/bin/env python3
"""Tests for the Book API REST Service."""

import unittest
import json
import os
import sqlite3

# Import app before setting environment
import sys
sys.path.insert(0, os.getcwd())

from app import app


class BookAPITestCase(unittest.TestCase):
    """Test cases for the Book API."""

    def setUp(self):
        """Set up test client and database."""
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Create an in-memory database for testing
        self.test_db_path = ':memory:'
        self.app_db = sqlite3.connect(self.test_db_path)
        self.app_db.row_factory = sqlite3.Row
        
        # Initialize schema
        cursor = self.app_db.cursor()
        cursor.execute('''
            CREATE TABLE books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        self.app_db.commit()
        
        # Monkey-patch get_db to return our in-memory database
        from app import get_db
        self.original_get_db = get_db
        
        def test_get_db():
            return self.app_db
        
        import app as app_module
        app_module.get_db = test_get_db
    
    def tearDown(self):
        """Clean up after each test."""
        self.app_db.close()
        # Restore original get_db
        import app as app_module
        app_module.get_db = self.original_get_db
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_list_books_empty(self):
        """Test listing books when database is empty."""
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, [])
    
    def test_create_book(self):
        """Test creating a new book."""
        book_data = {
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'year': 1925,
            'isbn': '978-0743273565'
        }
        response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], book_data['title'])
        self.assertEqual(data['author'], book_data['author'])
        self.assertEqual(data['year'], book_data['year'])
        self.assertEqual(data['isbn'], book_data['isbn'])
        self.assertIn('id', data)
        self.assertIn('created_at', data)
    
    def test_create_book_validation(self):
        """Test book creation validation."""
        # Missing title
        response = self.client.post(
            '/books',
            data=json.dumps({'author': 'Test Author'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
        # Missing author
        response = self.client.post(
            '/books',
            data=json.dumps({'title': 'Test Book'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
        # Empty title
        response = self.client.post(
            '/books',
            data=json.dumps({'title': '', 'author': 'Test Author'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_get_book_not_found(self):
        """Test getting a book that doesn't exist."""
        response = self.client.get('/books/999')
        self.assertEqual(response.status_code, 404)
    
    def test_get_book(self):
        """Test getting a single book."""
        # First create a book
        create_response = self.client.post(
            '/books',
            data=json.dumps({
                'title': 'To Kill a Mockingbird',
                'author': 'Harper Lee'
            }),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Then get it
        response = self.client.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'To Kill a Mockingbird')
        self.assertEqual(data['author'], 'Harper Lee')
    
    def test_update_book(self):
        """Test updating a book."""
        # First create a book
        create_response = self.client.post(
            '/books',
            data=json.dumps({
                'title': 'Original Title',
                'author': 'Original Author'
            }),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Update it
        update_data = {
            'title': 'Updated Title',
            'year': 2000
        }
        response = self.client.put(
            f'/books/{book_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Title')
        self.assertEqual(data['author'], 'Original Author')  # Unchanged
        self.assertEqual(data['year'], 2000)
    
    def test_update_book_not_found(self):
        """Test updating a book that doesn't exist."""
        response = self.client.put(
            '/books/999',
            data=json.dumps({'title': 'New Title'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
    
    def test_delete_book(self):
        """Test deleting a book."""
        # First create a book
        create_response = self.client.post(
            '/books',
            data=json.dumps({
                'title': 'Delete Me',
                'author': 'Delete Author'
            }),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Delete it
        response = self.client.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        # Verify it's gone
        get_response = self.client.get(f'/books/{book_id}')
        self.assertEqual(get_response.status_code, 404)
    
    def test_delete_book_not_found(self):
        """Test deleting a book that doesn't exist."""
        response = self.client.delete('/books/999')
        self.assertEqual(response.status_code, 404)
    
    def test_list_books_with_filter(self):
        """Test listing books with author filter."""
        # Create books with different authors
        self.client.post(
            '/books',
            data=json.dumps({'title': 'Book 1', 'author': 'Author A'}),
            content_type='application/json'
        )
        self.client.post(
            '/books',
            data=json.dumps({'title': 'Book 2', 'author': 'Author B'}),
            content_type='application/json'
        )
        self.client.post(
            '/books',
            data=json.dumps({'title': 'Book 3', 'author': 'Author A'}),
            content_type='application/json'
        )
        
        # Filter by author
        response = self.client.get('/books?author=Author%20A')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'Author A')


if __name__ == '__main__':
    unittest.main()
