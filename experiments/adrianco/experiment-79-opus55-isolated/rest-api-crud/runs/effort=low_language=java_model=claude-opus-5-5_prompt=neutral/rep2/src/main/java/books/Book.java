package books;

/** A book in the collection. {@code year} and {@code isbn} are optional. */
public record Book(Long id, String title, String author, Integer year, String isbn) {
    public Book withId(long newId) {
        return new Book(newId, title, author, year, isbn);
    }
}
