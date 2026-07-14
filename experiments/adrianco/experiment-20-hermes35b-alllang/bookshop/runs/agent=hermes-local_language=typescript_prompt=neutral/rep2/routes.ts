import { Request, Response, Router } from "express";
import {
  getAllBooks,
  getBookById,
  createBook,
  updateBook,
  deleteBook,
  Book,
} from "./db";

const router = Router();

// POST /books — Create a new book
router.post("/", (req: Request, res: Response) => {
  const { title, author, year, isbn } = req.body;

  // Validate required fields
  if (!title || !author) {
    return res.status(400).json({
      error: "Validation failed",
      message: "title and author are required fields",
    });
  }

  const book: Book = createBook(title, author, year, isbn);
  res.status(201).json(book);
});

// GET /books — List all books (optional author filter)
router.get("/", (_req: Request, res: Response) => {
  const author = _req.query.author as string | undefined;
  const books = author ? getAllBooks(author) : getAllBooks();
  res.json(books);
});

// GET /books/:id — Get a single book by ID
router.get("/:id", (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book ID" });
  }

  const book = getBookById(id);
  if (!book) {
    return res.status(404).json({ error: "Book not found" });
  }

  res.json(book);
});

// PUT /books/:id — Update a book
router.put("/:id", (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book ID" });
  }

  const { title, author, year, isbn } = req.body;

  // Validate required fields if provided
  if (title !== undefined && title === "") {
    return res.status(400).json({
      error: "Validation failed",
      message: "title cannot be empty",
    });
  }
  if (author !== undefined && author === "") {
    return res.status(400).json({
      error: "Validation failed",
      message: "author cannot be empty",
    });
  }

  const book = updateBook(id, title, author, year, isbn);
  if (!book) {
    return res.status(404).json({ error: "Book not found" });
  }

  res.json(book);
});

// DELETE /books/:id — Delete a book
router.delete("/:id", (req: Request, res: Response) => {
  const id = parseInt(req.params.id, 10);

  if (isNaN(id)) {
    return res.status(400).json({ error: "Invalid book ID" });
  }

  const deleted = deleteBook(id);
  if (!deleted) {
    return res.status(404).json({ error: "Book not found" });
  }

  res.status(204).send();
});

export default router;
