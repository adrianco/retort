#!/usr/bin/env python3
"""Integration tests for the Book API REST Service."""

import os
# Set test database before importing app
os.environ['BOOKS_DATABASE'] = 'test_books.db'

import unittest
import json
import tempfile
import shutil
from app import app, init_db, get_db
from flask import g

# Use a test database
TEST_DATABASE = 'test_books.db'


class BookAPITestCase(unittest.TestCase):
    """Test cases for the Book API."""

    def setUp(self):
        """Set up test fixtures."""
        # Override the database path for testing
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Remove any existing test database
        if os.path.exists(TEST_DATABASE):
            os.remove(TEST_DATABASE)
        
        # Initialize test database
        init_db()

    def tearDown(self):
        """Clean up after tests."""
        # Clear the database connection cache
        with app.app_context():
            g.pop('db', None)
        # Remove test database
        if os.path.exists(TEST_DATABASE):
            os.remove(TEST_DATABASE)

    def test_health_check(self):
        """Test the health check endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)

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

    def test_create_book_missing_title(self):
        """Test creating a book without title fails validation."""
        book_data = {
            'author': 'Some Author',
            'year': 2024
        }
        
        response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Title is required')

    def test_create_book_missing_author(self):
        """Test creating a book without author fails validation."""
        book_data = {
            'title': 'Some Book',
            'year': 2024
        }
        
        response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Author is required')

    def test_create_book_empty_title(self):
        """Test creating a book with empty title fails validation."""
        book_data = {
            'title': '',
            'author': 'Some Author'
        }
        
        response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Title is required')

    def test_list_books_empty(self):
        """Test listing books when database is empty."""
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['books'], [])

    def test_list_books_with_books(self):
        """Test listing books with some data."""
        # Create a book first
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1949
        }
        self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('books', data)
        self.assertEqual(len(data['books']), 1)
        self.assertEqual(data['books'][0]['title'], '1984')

    def test_list_books_filter_by_author(self):
        """Test listing books filtered by author."""
        # Create books
        book1 = {'title': 'Book 1', 'author': 'Author A', 'year': 2000}
        book2 = {'title': 'Book 2', 'author': 'Author B', 'year': 2001}
        book3 = {'title': 'Book 3', 'author': 'Author A', 'year': 2002}
        
        self.client.post('/books', data=json.dumps(book1), content_type='application/json')
        self.client.post('/books', data=json.dumps(book2), content_type='application/json')
        self.client.post('/books', data=json.dumps(book3), content_type='application/json')
        
        # Filter by author
        response = self.client.get('/books?author=Author A')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['books']), 2)
        for book in data['books']:
            self.assertEqual(book['author'], 'Author A')

    def test_get_book(self):
        """Test getting a single book by ID."""
        # Create a book
        book_data = {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee'
        }
        create_response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Get the book
        response = self.client.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'To Kill a Mockingbird')

    def test_get_book_not_found(self):
        """Test getting a book that doesn't exist."""
        response = self.client.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_update_book(self):
        """Test updating a book."""
        # Create a book
        book_data = {
            'title': 'Original Title',
            'author': 'Original Author',
            'year': 2000
        }
        create_response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Update the book
        update_data = {
            'title': 'Updated Title',
            'year': 2020
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
        self.assertEqual(data['year'], 2020)

    def test_update_book_not_found(self):
        """Test updating a book that doesn't exist."""
        update_data = {'title': 'New Title'}
        response = self.client.put('/books/999', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_update_book_empty_title(self):
        """Test updating a book with empty title fails validation."""
        # Create a book
        book_data = {'title': 'Original', 'author': 'Author'}
        create_response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Try to update with empty title
        update_data = {'title': ''}
        response = self.client.put(f'/books/{book_id}', data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_delete_book(self):
        """Test deleting a book."""
        # Create a book
        book_data = {'title': 'To Delete', 'author': 'Author'}
        create_response = self.client.post(
            '/books',
            data=json.dumps(book_data),
            content_type='application/json'
        )
        book_id = json.loads(create_response.data)['id']
        
        # Delete the book
        response = self.client.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('message', data)
        
        # Verify book is gone
        get_response = self.client.get(f'/books/{book_id}')
        self.assertEqual(get_response.status_code, 404)

    def test_delete_book_not_found(self):
        """Test deleting a book that doesn't exist."""
        response = self.client.delete('/books/999')
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
