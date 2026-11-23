package books;

import jakarta.validation.constraints.NotBlank;

record Book(long id, String title, String author, Integer year, String isbn) {
    record Input(@NotBlank String title, @NotBlank String author, Integer year, String isbn) {}
}
