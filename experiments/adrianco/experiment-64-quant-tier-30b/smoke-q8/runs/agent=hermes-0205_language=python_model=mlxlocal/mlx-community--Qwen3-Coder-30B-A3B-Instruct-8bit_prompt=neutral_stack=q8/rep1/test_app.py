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
        
        # Add a test book
        test_book = Book(
            title="Test Book",
            author="Test Author",
            year=2023,
            isbn="1234567890"
        )
        db.session.add(test_book)
        db.session.commit()

    def tearDown(self):
        """Clean up database after each test"""
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
            "title": "New Book",
            "author": "New Author",
            "year": 2024,
            "isbn": "0987654321"
        }
        
        response = self.app.post('/books', 
                                data=json.dumps(new_book),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'New Book')
        self.assertEqual(data['author'], 'New Author')
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['isbn'], '0987654321')

    def test_get_books(self):
        """Test getting all books"""
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'Test Book')

    def test_get_books_with_author_filter(self):
        """Test getting books with author filter"""
        response = self.app.get('/books?author=Test%20Author')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['author'], 'Test Author')

    def test_get_book_by_id(self):
        """Test getting a single book by ID"""
        response = self.app.get('/books/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')

    def test_update_book(self):
        """Test updating a book"""
        update_data = {
            "title": "Updated Book Title",
            "author": "Updated Author",
            "year": 2025,
            "isbn": "1111111111"
        }
        
        response = self.app.put('/books/1',
                               data=json.dumps(update_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Book Title')
        self.assertEqual(data['author'], 'Updated Author')
        self.assertEqual(data['year'], 2025)
        self.assertEqual(data['isbn'], '1111111111')

    def test_delete_book(self):
        """Test deleting a book"""
        response = self.app.delete('/books/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Book deleted successfully')
        
        # Verify book is deleted
        response = self.app.get('/books/1')
        self.assertEqual(response.status_code, 404)

    def test_create_book_missing_fields(self):
        """Test creating book with missing required fields"""
        invalid_book = {
            "title": "Invalid Book"
            # Missing author
        }
        
        response = self.app.post('/books',
                                data=json.dumps(invalid_book),
                                content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'Title and author are required')

if __name__ == '__main__':
    unittest.main()