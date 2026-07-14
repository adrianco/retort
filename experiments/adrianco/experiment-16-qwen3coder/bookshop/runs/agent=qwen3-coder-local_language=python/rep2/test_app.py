#!/usr/bin/env python3
"""
Unit and integration tests for the book collection REST API.
"""
import unittest
import json
from app import app, db, Book

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and database"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test book
        self.test_book = Book(
            title="Test Book",
            author="Test Author",
            year=2023,
            isbn="1234567890"
        )
        db.session.add(self.test_book)
        db.session.commit()
        
    def tearDown(self):
        """Tear down database and context"""
        db.session.remove()
        db.session.close()
        db.drop_all()
        self.app_context.pop()
        
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        
    def test_create_book(self):
        """Test creating a new book"""
        new_book = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0-452-28423-4'
        }
        
        response = self.app.post('/books',
                                data=json.dumps(new_book),
                                content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0-452-28423-4')
        
    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields"""
        incomplete_book = {
            'title': '1984'
            # Missing author
        }
        
        response = self.app.post('/books',
                                data=json.dumps(incomplete_book),
                                content_type='application/json')
        self.assertEqual(response.status_code, 400)
        
    def test_get_books(self):
        """Test getting all books"""
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book')
        
    def test_get_books_by_author(self):
        """Test getting books filtered by author"""
        # Add another book with the same author
        book2 = Book(
            title="Another Book",
            author="Test Author",
            year=2022
        )
        db.session.add(book2)
        db.session.commit()
        
        response = self.app.get('/books?author=Test Author')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        
        # Test with non-existent author
        response = self.app.get('/books?author=NonExistent')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)
        
    def test_get_book_by_id(self):
        """Test getting a single book by ID"""
        response = self.app.get(f'/books/{self.test_book.id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')
        self.assertEqual(data['id'], self.test_book.id)
        
    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        
    def test_update_book(self):
        """Test updating a book"""
        update_data = {
            'title': 'Updated Title',
            'year': 2024
        }
        
        response = self.app.put(f'/books/{self.test_book.id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Title')
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['author'], 'Test Author')  # Should remain unchanged
        
    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist"""
        update_data = {
            'title': 'Updated Title'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(update_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 404)
        
    def test_delete_book(self):
        """Test deleting a book"""
        response = self.app.delete(f'/books/{self.test_book.id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')
        
        # Verify book is deleted
        response = self.app.get(f'/books/{self.test_book.id}')
        self.assertEqual(response.status_code, 404)
        
    def test_delete_nonexistent_book(self):
        """Test deleting a book that doesn't exist"""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()