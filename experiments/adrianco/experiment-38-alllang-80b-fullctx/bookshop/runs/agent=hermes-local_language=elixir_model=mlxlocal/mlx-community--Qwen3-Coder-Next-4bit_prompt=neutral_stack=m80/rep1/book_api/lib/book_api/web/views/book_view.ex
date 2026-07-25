defmodule BookApi.BookView do
  use BookApi.Web, :view

  def render("index.json", %{books: books}) do
    %{data: books}
  end

  def render("show.json", %{book: book}) do
    %{data: book}
  end

  def render("error.json", %{errors: errors}) do
    %{errors: errors}
  end
end
