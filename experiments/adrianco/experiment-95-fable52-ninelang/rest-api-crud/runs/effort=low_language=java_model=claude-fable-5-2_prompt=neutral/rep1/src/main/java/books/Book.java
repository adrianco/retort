package books;

/** A book. {@code year} and {@code isbn} are optional; {@code id} is null until persisted. */
public record Book(Long id, String title, String author, Integer year, String isbn) {
}
