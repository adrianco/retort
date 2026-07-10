#!/usr/bin/env python
"""
Simple script to run the book API server
"""
import os
from app import app

if __name__ == '__main__':
    # Set debug mode to True for development
    app.run(debug=True, host='0.0.0.0', port=5000)
