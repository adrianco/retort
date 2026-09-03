import unittest
import tempfile
import os
import sys
import json
sys.path.insert(0, '/Users/adriancockcroft/.retort/work/retort-local-srep150x/retort-0c13f42281bc')

from app import app

class BookAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_create_book(self):
        """Test creating a book"""
        response = self.client.post('/books', 
                                    data=json.dumps({
                                        'title': 'Test Book', 
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Book')
        self.assertEqual(data['author'], 'Test Author')

if __name__ == '__main__':
    unittest.main()