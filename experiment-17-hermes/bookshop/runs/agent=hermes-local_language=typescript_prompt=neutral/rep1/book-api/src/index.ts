import express, { Application, Request, Response } from "express";
import { BookService } from "./book-service";
import { Book } from "./book";

const app: Application = express();
const port = process.env.PORT || 3000;

app.use(express.json());

const bookService = new BookService();

// Health check endpoint
app.get("/health", (req: Request, res: Response) => {
  res.status(200).json({ status: "OK" });
});

// Create a new book
app.post("/books", (req: Request, res: Response) => {
  try {
    const book = bookService.createBook(req.body);
    res.status(201).json(book);
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Get all books
app.get("/books", (req: Request, res: Response) => {
  try {
    const author = req.query.author as string;
    const books = bookService.getAllBooks(author);
    res.status(200).json(books);
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Get a single book by ID
app.get("/books/:id", (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const book = bookService.getBookById(id);
    if (book) {
      res.status(200).json(book);
    } else {
      res.status(404).json({ error: "Book not found" });
    }
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

// Update a book
app.put("/books/:id", (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const book = bookService.updateBook(id, req.body);
    if (book) {
      res.status(200).json(book);
    } else {
      res.status(404).json({ error: "Book not found" });
    }
  } catch (error: any) {
    res.status(400).json({ error: error.message });
  }
});

// Delete a book
app.delete("/books/:id", (req: Request, res: Response) => {
  try {
    const id = parseInt(req.params.id);
    const deleted = bookService.deleteBook(id);
    if (deleted) {
      res.status(200).json({ message: "Book deleted successfully" });
    } else {
      res.status(404).json({ error: "Book not found" });
    }
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});

export default app;
