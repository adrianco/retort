import unittest
import json
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import app

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
    def tearDown(self):
        self.app_context.pop()

    def test_health_check(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        response = self.app.post('/books', 
                                 data=json.dumps({
                                     "title": "Test Book",
                                     "author": "Test Author",
                                     "year": 2023,
     "isbn": "1234567890"
                                 }),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], "Test Book")
        self.assertEqual(data['author'], "Test Author")
        self.assertEqual(data['year'], 2023)
        self.assertEqual(data['isbn'], "1234567890")

    def test_get_all_books(self):
        response = self.app.get('/books')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_get_book_by_id(self):
        # First create a book to get an ID
        response = self.app.post('/books', 
                                 data=json.dumps({
                                     "title": "Test Book",
     "author": "Test Author",
     "year": 2023,
     "isbn": "1234567890"
                                 }),
                                 content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], "Test Book")
        self.assertEqual(data['author'], "Test Author")
        
    def test_update_book(self):
        # First create a book to update
        response = self.app.post('/books', 
                                 data=json.dumps({
     "title": "Test Book",
     "author": "Test Author",
     "year": 2023,
     "isbn": "1234567890"
                                 }),
                                 content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        response = self.app.put(f'/books/{book_id}', 
                                data=json.dumps({
                                    "title": "Updated Book",
                                    "author": "Updated Author",
                                    "year": 2024,
                                    "isbn": "0987654321"
                                }),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], "Updated Book")
        self.assertEqual(data['author'], "Updated Author")
        self.assertEqual(data['year'], 2024)
        self.assertEqual(data['isbn'], "0987654321")
        
    def test_delete_book(self):
        # First create a book to delete
        response = self.app.post('/books', 
                                 data=json.dumps({
     "title": "Test Book",
     "author": "Test Author", 
     "year": 2023,
     "isbn": "1234567890"
                                 }),
                                 content_type='application/json')
        data = json.loads(response.data)
        book_id = data['id']
        
        response = self.app.delete(f'/books/{book_id}')
        self.assertEqual(response.status_code, 200)
        
        # Try to get the deleted book
        response = self.app.get(f'/books/{book_id}')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()