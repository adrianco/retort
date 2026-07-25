import { DatabaseService } from '../src/database';
import { BookService, CreateBookInput, UpdateBookInput } from '../src/services/BookService';

describe('BookService Unit Tests', () => {
  let dbService: DatabaseService;
  let bookService: BookService;

  beforeAll(async () => {
    // Use in-memory database
    dbService = new DatabaseService(':memory:');
    bookService = new BookService(dbService);
  });

  afterAll(async () => {
    await dbService.close();
  });

  describe('createBook', () => {
    it('should create a book with all fields', async () => {
      const input: CreateBookInput = {
        title: 'Test Book',
        author: 'Test Author',
        year: 2024,
        isbn: '123-4567890123'
      };

      const book = await bookService.createBook(input);

      expect(book).toBeDefined();
      expect(book.title).toBe(input.title);
      expect(book.author).toBe(input.author);
      expect(book.year).toBe(input.year);
      expect(book.isbn).toBe(input.isbn);
      expect(book.id).toBeDefined();
      expect(book.createdAt).toBeDefined();
      expect(book.updatedAt).toBeDefined();
    });
  });

  describe('getBookById', () => {
    let createdBook: any;

    beforeAll(async () => {
      createdBook = await bookService.createBook({
        title: 'Find Me',
        author: 'Finder',
        year: 2020,
        isbn: '978-1234567890'
      });
    });

    it('should return a book by ID', async () => {
      const book = await bookService.getBookById(createdBook.id);

      expect(book).toBeDefined();
      expect(book?.id).toBe(createdBook.id);
    });

    it('should return null for non-existent book', async () => {
      const book = await bookService.getBookById('non-existent-id');
      expect(book).toBeNull();
    });
  });

  describe('getAllBooks', () => {
    beforeEach(async () => {
      // Ensure table exists
      await dbService.query('SELECT 1');
    });

    it('should return all books', async () => {
      const books = await bookService.getBooks();

      expect(Array.isArray(books)).toBe(true);
      expect(books.length).toBeGreaterThan(0);
    });

    it('should filter books by author', async () => {
      // Create test books for this test
      await bookService.createBook({
        title: 'Book A',
        author: 'Author X',
        year: 2020,
        isbn: '111-1111111111'
      });

      await bookService.createBook({
        title: 'Book B',
        author: 'Author Y',
        year: 2021,
        isbn: '222-2222222222'
      });

      await bookService.createBook({
        title: 'Book C',
        author: 'Author X',
        year: 2022,
        isbn: '333-3333333333'
      });

      const books = await bookService.getBooks('Author X');

      expect(Array.isArray(books)).toBe(true);
      expect(books.length).toBe(2);
      expect(books.every((b: any) => b.author === 'Author X')).toBe(true);
    });

    it('should return empty array for non-existent author', async () => {
      const books = await bookService.getBooks('Non Existent');

      expect(Array.isArray(books)).toBe(true);
      expect(books.length).toBe(0);
    });
  });

  describe('updateBook', () => {
    let createdBook: any;

    beforeAll(async () => {
      createdBook = await bookService.createBook({
        title: 'Original Title',
        author: 'Original Author',
        year: 2020,
        isbn: '123-4567890123'
      });
    });

    it('should update a book', async () => {
      const updateData: UpdateBookInput = {
        title: 'Updated Title',
        year: 2021
      };

      const book = await bookService.updateBook(createdBook.id, updateData);

      expect(book).toBeDefined();
      expect(book?.title).toBe(updateData.title);
      expect(book?.year).toBe(updateData.year);
      expect(book?.author).toBe(createdBook.author); // Unchanged
    });

    it('should return null for non-existent book', async () => {
      const book = await bookService.updateBook('non-existent-id', { title: 'Test' });
      expect(book).toBeNull();
    });

    it('should return existing book when no updates provided', async () => {
      const book = await bookService.updateBook(createdBook.id, {});
      expect(book).toBeDefined();
      expect(book?.id).toBe(createdBook.id);
    });
  });

  describe('deleteBook', () => {
    let createdBook: any;

    beforeAll(async () => {
      createdBook = await bookService.createBook({
        title: 'To Delete',
        author: 'Delete Author',
        year: 2020,
        isbn: '123-4567890123'
      });
    });

    it('should delete a book', async () => {
      const deleted = await bookService.deleteBook(createdBook.id);
      expect(deleted).toBe(true);

      // Verify book is gone
      const book = await bookService.getBookById(createdBook.id);
      expect(book).toBeNull();
    });

    it('should return false for non-existent book', async () => {
      const deleted = await bookService.deleteBook('non-existent-id');
      expect(deleted).toBe(false);
    });
  });
});
