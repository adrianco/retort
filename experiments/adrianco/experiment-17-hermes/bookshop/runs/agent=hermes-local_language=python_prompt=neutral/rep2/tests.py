import unittest
import json
from app import app, init_db

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        # Set up test client
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize database
        init_db()
    
    def tearDown(self):
        self.app_context.pop()
    
    def test_health_check(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_create_book(self):
        # Test creating a book
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
    
    def test_create_book_missing_fields(self):
        # Test creating a book with missing required fields
        book_data = {
            'title': 'Test Book',
            # Missing author
            'year': 2023
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_get_all_books(self):
        # Add a test book
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
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book')
    
    def test_get_books_by_author(self):
        # Add test books
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
        
        # Get books by author A
        response = self.app.get('/books?author=Author A')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['author'], 'Author A')
    
    def test_get_single_book(self):
        # Add a test book
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
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')
    
    def test_update_book(self):
        # Add a test book
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
        updated_data = {
            'title': 'Updated Book',
            'author': 'Updated Author'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(updated_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')
    
    def test_delete_book(self):
        # Add a test book
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
    
    def test_delete_nonexistent_book(self):
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Book not found')

if __name__ == '__main__':
    unittest.main()
