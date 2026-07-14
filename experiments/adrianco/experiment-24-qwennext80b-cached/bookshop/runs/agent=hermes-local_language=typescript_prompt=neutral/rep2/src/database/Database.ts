import fs from 'fs';
import path from 'path';

const DB_PATH = process.env.DB_PATH || ':memory:';

interface BookRow {
  id: number;
  title: string;
  author: string;
  year: number;
  isbn: string;
  createdAt: string;
  updatedAt: string;
}

class DatabaseManager {
  private data: BookRow[];

  constructor() {
    if (DB_PATH === ':memory:') {
      this.data = [];
    } else {
      try {
        const data = fs.readFileSync(DB_PATH, 'utf8');
        this.data = JSON.parse(data);
      } catch (e) {
        this.data = [];
      }
    }
  }

  private save(): void {
    if (DB_PATH !== ':memory:') {
      fs.writeFileSync(DB_PATH, JSON.stringify(this.data, null, 2));
    }
  }

  getAll(): BookRow[] {
    return [...this.data];
  }

  getById(id: number): BookRow | undefined {
    return this.data.find(book => book.id === id);
  }

  getByAuthor(author: string): BookRow[] {
    return this.data.filter(book => book.author === author);
  }

  create(book: Omit<BookRow, 'id' | 'createdAt' | 'updatedAt'>): BookRow {
    const id = this.data.length > 0 
      ? Math.max(...this.data.map(b => b.id)) + 1 
      : 1;
    const now = new Date().toISOString();
    const newBook: BookRow = {
      id,
      ...book,
      createdAt: now,
      updatedAt: now,
    };
    this.data.push(newBook);
    this.save();
    return newBook;
  }

  update(id: number, book: Partial<Omit<BookRow, 'id'>>): BookRow | undefined {
    const index = this.data.findIndex(b => b.id === id);
    if (index === -1) return undefined;
    
    const now = new Date().toISOString();
    const existing = this.data[index];
    const updatedBook: BookRow = {
      ...existing,
      ...book,
      updatedAt: now,
    };
    this.data[index] = updatedBook;
    this.save();
    return updatedBook;
  }

  delete(id: number): boolean {
    const index = this.data.findIndex(b => b.id === id);
    if (index === -1) return false;
    this.data.splice(index, 1);
    this.save();
    return true;
  }

  close(): void {
    this.save();
  }
}

export const db = new DatabaseManager();
