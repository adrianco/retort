import { BookService } from "./book-service";
import { Book } from "./book";

describe("BookService", () => {
  let bookService: BookService;

  beforeEach(async () => {
    bookService = new BookService();
    // Clear the database before each test
    await bookService["db"].exec("DELETE FROM books");
  });

  it("should create a book", async () => {
    const bookData = {
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925,
      isbn: "978-0-7432-7356-5"
    };

    const createdBook = await bookService.createBook(bookData);
    
    expect(createdBook).toEqual({
      id: expect.any(Number),
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925,
      isbn: "978-0-7432-7356-5"
    });
  });

  it("should not create a book without title and author", async () => {
    expect.assertions(1);
    
    try {
      await bookService.createBook({ title: "", author: "" });
    } catch (error: any) {
      expect(error.message).toBe("Title and author are required");
    }
  });

  it("should get all books", async () => {
    // Create test books
    await bookService.createBook({
      title: "Book 1",
      author: "Author 1",
      year: 2020
    });
    
    await bookService.createBook({
      title: "Book 2",
      author: "Author 2",
      year: 2021
    });

    const books = await bookService.getAllBooks();
    
    expect(books).toHaveLength(2);
    expect(books[0]).toEqual({
      id: expect.any(Number),
      title: "Book 1",
      author: "Author 1",
      year: 2020,
      isbn: null
    });
  });

  it("should get books filtered by author", async () => {
    // Create test books with different authors
    await bookService.createBook({
      title: "Book 1",
      author: "Author 1",
      year: 2020
    });
    
    await bookService.createBook({
      title: "Book 2",
      author: "Author 2",
      year: 2021
    });

    const books = await bookService.getAllBooks("Author 1");
    
    expect(books).toHaveLength(1);
    expect(books[0].author).toBe("Author 1");
  });

  it("should get a book by ID", async () => {
    const createdBook = await bookService.createBook({
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925
    });

    const book = await bookService.getBookById(createdBook.id!);
    
    expect(book).toEqual({
      id: createdBook.id,
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925,
      isbn: null
    });
  });

  it("should update a book", async () => {
    const createdBook = await bookService.createBook({
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925
    });

    const updatedBook = await bookService.updateBook(createdBook.id!, {
      title: "The Great Gatsby Updated",
      year: 1926
    });

    expect(updatedBook).toEqual({
      id: createdBook.id,
      title: "The Great Gatsby Updated",
      author: "F. Scott Fitzgerald",
      year: 1926,
      isbn: null
    });
  });

  it("should delete a book", async () => {
    const createdBook = await bookService.createBook({
      title: "The Great Gatsby",
      author: "F. Scott Fitzgerald",
      year: 1925
    });

    const deleted = await bookService.deleteBook(createdBook.id!);
    
    expect(deleted).toBe(true);
  });
});
