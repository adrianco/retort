#!/usr/bin/env python3
"""
HTTP Server for Book Collection API - Complete implementation
"""

import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import re

# Make sure we can import our module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from book_api import BookAPI

# Initialize the API
api = BookAPI()

class BookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        
        # Health check
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"status": "healthy"}
            self.wfile.write(json.dumps(response).encode())
            return
            
        # List all books or filter by author
        if path == "/books":
            try:
                author = query_params.get("author", [None])[0]
                books = api.list_books(author)
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(books).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
            return
            
        # Get a single book by ID
        match = re.match(r"/books/(\d+)", path)
        if match:
            try:
                book_id = int(match.group(1))
                book = api.get_book(book_id)
                
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(book).encode())
            except ValueError as e:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
            return
            
        # Invalid endpoint
        self.send_response(404)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"error": "Endpoint not found"}
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        if self.path != "/books":
            self.send_response(404)
            self.end_headers()
            return
            
        # Read the request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            book_data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Invalid JSON"}
            self.wfile.write(json.dumps(response).encode())
            return
            
        # Validate required fields
        if not book_data.get("title") or not book_data.get("author"):
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Title and author are required"}
            self.wfile.write(json.dumps(response).encode())
            return
            
        try:
            # Create the book
            created_book = api.create_book(book_data)
            
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(created_book).encode())
        except ValueError as e:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def do_PUT(self):
        match = re.match(r"/books/(\d+)", self.path)
        if not match:
            self.send_response(404)
            self.end_headers()
            return
            
        book_id = int(match.group(1))
        
        # Read the request body
        content_length = int(self.headers['Content-Length'])
        put_data = self.rfile.read(content_length)
        try:
            book_data = json.loads(put_data.decode('utf-8'))
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": "Invalid JSON"}
            self.wfile.write(json.dumps(response).encode())
            return
            
        try:
            # Update the book
            updated_book = api.update_book(book_id, book_data)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(updated_book).encode())
        except ValueError as e:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def do_DELETE(self):
        match = re.match(r"/books/(\d+)", self.path)
        if not match:
            self.send_response(404)
            self.end_headers()
            return
            
        book_id = int(match.group(1))
        
        try:
            # Delete the book
            result = api.delete_book(book_id)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except ValueError as e:
            self.send_response(404)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"error": str(e)}
            self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, BookHandler)
    print(f"Starting server on port {port}")
    print("Endpoints:")
    print("  GET    /health          - Health check")
    print("  GET    /books           - List all books")
    print("  GET    /books/{id}      - Get a book by ID")
    print("  POST   /books           - Create a book")
    print("  PUT    /books/{id}      - Update a book")
    print("  DELETE /books/{id}      - Delete a book")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    run_server()