import { serve } from "bun";
import { Database } from "bun:sqlite";

// Define types
interface Book {
  id: string;
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
}

// Initialize database
const db = new Database("books.db");
db.run(`
  CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    year INTEGER,
    isbn TEXT
  )
`);

// Helper function to validate book data
function validateBookData(book: Partial<Book>): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  if (!book.title || typeof book.title !== 'string' || book.title.trim() === '') {
    errors.push('Title is required');
  }
  
  if (!book.author || typeof book.author !== 'string' || book.author.trim() === '') {
    errors.push('Author is required');
  }
  
  if (book.year !== undefined && book.year !== null && (typeof book.year !== 'number' || book.year < 1000 || book.year > 2100)) {
    errors.push('Year must be a valid year between 1000 and 2100 or null');
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}

// Helper function to get books by author (filter)
function getBooksByAuthor(author: string): Book[] {
  const stmt = db.prepare("SELECT * FROM books WHERE author LIKE ? ORDER BY title");
  return stmt.all(`%${author}%`) as Book[];
}

// Health check endpoint
function healthHandler(): Response {
  return new Response(
    JSON.stringify({ status: "healthy", timestamp: new Date().toISOString() }),
    {
      headers: { "Content-Type": "application/json" }
    }
  );
}

// Get all books
function getAllBooksHandler(request: Request): Response {
  const url = new URL(request.url);
  const author = url.searchParams.get('author') || '';
  
  let books: Book[];
  
  if (author) {
    books = getBooksByAuthor(author);
  } else {
    const stmt = db.prepare("SELECT * FROM books ORDER BY title");
    books = stmt.all() as Book[];
  }
  
  return new Response(
    JSON.stringify(books),
    {
      headers: { "Content-Type": "application/json" }
    }
  );
}

// Get a single book by ID
function getBookByIdHandler(id: string): Response {
  const stmt = db.prepare("SELECT * FROM books WHERE id = ?");
  const book = stmt.get(id) as Book | null;
  
  if (!book) {
    return new Response(
      JSON.stringify({ error: "Book not found" }),
      {
        status: 404,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
  
  return new Response(
    JSON.stringify(book),
    {
      headers: { "Content-Type": "application/json" }
    }
  );
}

// Create a new book
async function createBookHandler(request: Request): Promise<Response> {
  try {
    const body = await request.json();
    
    const validation = validateBookData(body);
    if (!validation.isValid) {
      return new Response(
        JSON.stringify({ errors: validation.errors }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" }
        }
      );
    }
    
    const id = crypto.randomUUID();
    const { title, author, year, isbn } = body;
    
    const stmt = db.prepare("INSERT INTO books (id, title, author, year, isbn) VALUES (?, ?, ?, ?, ?)");
    stmt.run(id, title, author, year || null, isbn || null);
    
    const newBook = { id, title, author, year: year || null, isbn: isbn || null };
    
    return new Response(
      JSON.stringify(newBook),
      {
        status: 201,
        headers: { "Content-Type": "application/json" }
      }
    );
  } catch (error: any) {
    return new Response(
      JSON.stringify({ error: "Invalid JSON data" }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
}

// Update a book
async function updateBookHandler(request: Request, id: string): Promise<Response> {
  const book = db.prepare("SELECT * FROM books WHERE id = ?").get(id) as Book | null;
  
  if (!book) {
    return new Response(
      JSON.stringify({ error: "Book not found" }),
      {
        status: 404,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
  
  try {
    const body = await request.json();
    
    const validation = validateBookData(body);
    if (!validation.isValid) {
      return new Response(
        JSON.stringify({ errors: validation.errors }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" }
        }
      );
    }
    
    const { title, author, year, isbn } = body;
    
    const stmt = db.prepare("UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?");
    stmt.run(title, author, year || null, isbn || null, id);
    
    const updatedBook = { id, title, author, year: year || null, isbn: isbn || null };
    
    return new Response(
      JSON.stringify(updatedBook),
      {
        headers: { "Content-Type": "application/json" }
      }
    );
  } catch (error: any) {
    return new Response(
      JSON.stringify({ error: "Invalid JSON data" }),
      {
        status: 400,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
}

// Delete a book
function deleteBookHandler(id: string): Response {
  const stmt = db.prepare("DELETE FROM books WHERE id = ?");
  const result = stmt.run(id);
  
  if (result.changes === 0) {
    return new Response(
      JSON.stringify({ error: "Book not found" }),
      {
        status: 404,
        headers: { "Content-Type": "application/json" }
      }
    );
  }
  
  return new Response(
    JSON.stringify({ message: "Book deleted successfully" }),
    {
      headers: { "Content-Type": "application/json" }
    }
  );
}

// Main server function
async function handleRequest(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const method = request.method;
  const path = url.pathname;
  
  // Parse ID from path for book-related operations
  const pathParts = path.split('/').filter(part => part);
  
  if (path === '/health' && method === 'GET') {
    return healthHandler();
  }
  
  if (path === '/books' && method === 'GET') {
    return getAllBooksHandler(request);
  }
  
  if (path === '/books' && method === 'POST') {
    return createBookHandler(request);
  }
  
  if (pathParts.length === 2 && pathParts[0] === 'books' && method === 'GET') {
    const id = pathParts[1];
    return getBookByIdHandler(id);
  }
  
  if (pathParts.length === 2 && pathParts[0] === 'books' && method === 'PUT') {
    const id = pathParts[1];
    return updateBookHandler(request, id);
  }
  
  if (pathParts.length === 2 && pathParts[0] === 'books' && method === 'DELETE') {
    const id = pathParts[1];
    return deleteBookHandler(id);
  }
  
  return new Response(
    JSON.stringify({ error: "Not found" }),
    {
      status: 404,
      headers: { "Content-Type": "application/json" }
    }
  );
}

// Start the server
serve({
  fetch: handleRequest,
  port: 3000,
  hostname: "localhost"
});

console.log("Server running on http://localhost:3000");