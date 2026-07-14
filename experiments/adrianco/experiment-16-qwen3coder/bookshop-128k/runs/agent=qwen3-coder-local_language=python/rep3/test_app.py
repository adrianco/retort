import unittest
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and initialize database"""
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        init_db()
        
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
        # Clean up database file
        if os.path.exists('books.db'):
            os.remove('books.db')
            
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        
    def test_create_book(self):
        """Test creating a new book"""
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0451524935')
        self.assertIn('id', data)
        
    def test_create_book_missing_fields(self):
        """Test creating a book with missing required fields"""
        book_data = {
            'title': '1984'
            # Missing author
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_get_all_books(self):
        """Test getting all books"""
        # First create a book
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        self.app.post('/books', 
                     data=json.dumps(book_data),
                     content_type='application/json')
        
        # Get all books
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], '1984')
        
    def test_get_books_by_author(self):
        """Test getting books filtered by author"""
        # Create multiple books
        book1 = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        book2 = {
            'title': 'Animal Farm',
            'author': 'George Orwell',
            'year': 1945,
            'isbn': '978-0451526342'
        }
        
        book3 = {
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'year': 1960,
            'isbn': '978-0061120084'
        }
        
        self.app.post('/books', data=json.dumps(book1), content_type='application/json')
        self.app.post('/books', data=json.dumps(book2), content_type='application/json')
        self.app.post('/books', data=json.dumps(book3), content_type='application/json')
        
        # Get books by author
        response = self.app.get('/books?author=George%20Orwell')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'George Orwell')
            
    def test_get_single_book(self):
        """Test getting a single book by ID"""
        # Create a book
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        book_id = json.loads(response.data)['id']
        
        # Get the book by ID
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0451524935')
        self.assertEqual(data['id'], book_id)
        
    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_update_book(self):
        """Test updating a book"""
        # Create a book
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        book_id = json.loads(response.data)['id']
        
        # Update the book
        updated_data = {
            'title': 'Nineteen Eighty-Four',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        response = self.app.put(f'/books/{book_id}',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Nineteen Eighty-Four')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0451524935')
        self.assertEqual(data['id'], book_id)
        
    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist"""
        updated_data = {
            'title': 'Nineteen Eighty-Four',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)
        
    def test_delete_book(self):
        """Test deleting a book"""
        # Create a book
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
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
        
        # Verify book is deleted
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)
        
    def test_delete_nonexistent_book(self):
        """Test deleting a book that doesn't exist"""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertIn('error', data)

if __name__ == '__main__':
    unittest.main()