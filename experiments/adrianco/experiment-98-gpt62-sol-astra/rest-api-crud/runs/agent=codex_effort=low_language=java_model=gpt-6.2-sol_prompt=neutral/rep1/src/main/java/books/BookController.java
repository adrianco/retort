package books;

import java.net.URI;
import java.util.List;
import java.util.Map;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
class BookController {
    private final BookRepository books;

    BookController(BookRepository books) {
        this.books = books;
    }

    @GetMapping("/health")
    Map<String, String> health() {
        return Map.of("status", "UP");
    }

    @PostMapping("/books")
    ResponseEntity<Book> create(@Valid @RequestBody Book.Input input) {
        Book book = books.create(input);
        return ResponseEntity.created(URI.create("/books/" + book.id())).body(book);
    }

    @GetMapping("/books")
    List<Book> list(@RequestParam(required = false) String author) {
        return books.list(author);
    }

    @GetMapping("/books/{id}")
    Book find(@PathVariable long id) {
        return books.find(id).orElseThrow(this::notFound);
    }

    @PutMapping("/books/{id}")
    Book update(@PathVariable long id, @Valid @RequestBody Book.Input input) {
        return books.update(id, input).orElseThrow(this::notFound);
    }

    @DeleteMapping("/books/{id}")
    ResponseEntity<Void> delete(@PathVariable long id) {
        if (!books.delete(id)) {
            throw notFound();
        }
        return ResponseEntity.noContent().build();
    }

    private ResponseStatusException notFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "Book not found");
    }
}
