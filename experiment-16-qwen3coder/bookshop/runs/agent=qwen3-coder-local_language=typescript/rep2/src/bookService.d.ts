export interface Book {
    id: number;
    title: string;
    author: string;
    year?: number;
    isbn?: string;
}
export interface BookInput {
    title: string;
    author: string;
    year?: number;
    isbn?: string;
}
export declare class BookService {
    getAllBooks(author?: string): Promise<Book[]>;
    getBookById(id: number): Promise<Book | null>;
    createBook(bookData: BookInput): Promise<Book>;
    updateBook(id: number, bookData: Partial<BookInput>): Promise<Book | null>;
    deleteBook(id: number): Promise<boolean>;
}
//# sourceMappingURL=bookService.d.ts.map