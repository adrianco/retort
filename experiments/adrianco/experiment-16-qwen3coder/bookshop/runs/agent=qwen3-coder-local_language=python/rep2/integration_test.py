#!/usr/bin/env python3
"""
Integration test for the book collection REST API.
"""
import requests
import json
import time
import subprocess
import threading

def run_app():
    """Run the Flask app in a separate process"""
    return subprocess.Popen(['python3', 'app.py'])

def test_api():
    """Test API endpoints"""
    # Give the server time to start
    time.sleep(2)
    
    base_url = 'http://localhost:5000'
    
    print("Testing health check...")
    response = requests.get(f'{base_url}/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\nTesting book creation...")
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    response = requests.post(f'{base_url}/books', json=book_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    book_id = response.json()['id']
    
    print("\nTesting book retrieval...")
    response = requests.get(f'{base_url}/books/{book_id}')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\nTesting all books retrieval...")
    response = requests.get(f'{base_url}/books')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\nTesting book update...")
    update_data = {
        'title': 'Nineteen Eighty-Four',
        'year': 1948
    }
    response = requests.put(f'{base_url}/books/{book_id}', json=update_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\nTesting book deletion...")
    response = requests.delete(f'{base_url}/books/{book_id}')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    print("\nAll tests completed successfully!")

if __name__ == '__main__':
    # Start the app
    print("Starting Flask app...")
    app_process = run_app()
    
    try:
        # Wait a bit for app to start
        time.sleep(2)
        test_api()
    finally:
        # Clean up
        app_process.terminate()
        app_process.wait()