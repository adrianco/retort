defmodule BookApiWeb.BookView do
  use BookApiWeb, :view

  def render("index.json", %{books: books}) do
    %{data: render_many(books, BookApiWeb.BookView, "book.json")}
  end

  def render("show.json", %{book: book}) do
    %{data: render_one(book, BookApiWeb.BookView, "book.json")}
  end

  def render("book.json", %{book: book}) do
    %{
      id: book.id,
      title: book.title,
      author: book.author,
      year: book.year,
      isbn: book.isbn,
      inserted_at: book.inserted_at,
      updated_at: book.updated_at
    }
  end
end
