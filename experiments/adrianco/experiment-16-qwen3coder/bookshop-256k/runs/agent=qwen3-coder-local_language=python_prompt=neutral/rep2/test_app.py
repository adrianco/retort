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
        
    def tearDown(self):
        """Tear down database after each test"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
    
    def test_create_book(self):
        """Test creating a new book"""
        book_data = {
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0-452-28423-4'
        }
        
        response = self.app.post('/books',
                                data=json.dumps(book_data),
                                content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
        self.assertEqual(data['year'], 1948)
        self.assertEqual(data['isbn'], '978-0-452-28423-4')
        
        # Verify book was saved to database
        book = Book.query.get(data['id'])
        self.assertIsNotNone(book)
        self.assertEqual(book.title, '1984')
    
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
    
    def test_get_all_books(self):
        """Test getting all books"""
        # Create test books
        book1 = Book(title='1984', author='George Orwell', year=1948)
        book2 = Book(title='To Kill a Mockingbird', author='Harper Lee', year=1960)
        
        db.session.add(book1)
        db.session.add(book2)
        db.session.commit()
        
        response = self.app.get('/books')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 2)
        
    def test_get_books_by_author(self):
        """Test getting books filtered by author"""
        # Create test books
        book1 = Book(title='1984', author='George Orwell', year=1948)
        book2 = Book(title='Animal Farm', author='George Orwell', year=1945)
        book3 = Book(title='To Kill a Mockingbird', author='Harper Lee', year=1960)
        
        db.session.add(book1)
        db.session.add(book2)
        db.session.add(book3)
        db.session.commit()
        
        response = self.app.get('/books?author=George%20Orwell')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), 2)
        for book in data:
            self.assertEqual(book['author'], 'George Orwell')
    
    def test_get_single_book(self):
        """Test getting a single book by ID"""
        # Create test book
        book = Book(title='1984', author='George Orwell', year=1948)
        db.session.add(book)
        db.session.commit()
        
        response = self.app.get(f'/books/{book.id}')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], '1984')
        self.assertEqual(data['author'], 'George Orwell')
    
    def test_get_nonexistent_book(self):
        """Test getting a book that doesn't exist"""
        response = self.app.get('/books/999')
        self.assertEqual(response.status_code, 404)
    
    def test_update_book(self):
        """Test updating a book"""
        # Create test book
        book = Book(title='1984', author='George Orwell', year=1948)
        db.session.add(book)
        db.session.commit()
        
        update_data = {
            'title': 'Nineteen Eighty-Four',
            'year': 1949
        }
        
        response = self.app.put(f'/books/{book.id}',
                               data=json.dumps(update_data),
                               content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], 'Nineteen Eighty-Four')
        self.assertEqual(data['year'], 1949)
        self.assertEqual(data['author'], 'George Orwell')  # Should remain unchanged
    
    def test_update_nonexistent_book(self):
        """Test updating a book that doesn't exist"""
        update_data = {
            'title': 'Nineteen Eighty-Four'
        }
        
        response = self.app.put('/books/999',
                               data=json.dumps(update_data),
                               content_type='application/json')
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_book(self):
        """Test deleting a book"""
        # Create test book
        book = Book(title='1984', author='George Orwell', year=1948)
        db.session.add(book)
        db.session.commit()
        
        response = self.app.delete(f'/books/{book.id}')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['message'], 'Book deleted successfully')
        
        # Verify book was deleted
        deleted_book = Book.query.get(book.id)
        self.assertIsNone(deleted_book)
    
    def test_delete_nonexistent_book(self):
        """Test deleting a book that doesn't exist"""
        response = self.app.delete('/books/999')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()