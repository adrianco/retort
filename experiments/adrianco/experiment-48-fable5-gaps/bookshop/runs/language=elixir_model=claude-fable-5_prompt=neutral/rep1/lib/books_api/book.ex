defmodule BooksApi.Book do
  use Ecto.Schema
  import Ecto.Changeset

  @derive {Jason.Encoder, only: [:id, :title, :author, :year, :isbn]}
  schema "books" do
    field(:title, :string)
    field(:author, :string)
    field(:year, :integer)
    field(:isbn, :string)

    timestamps()
  end

  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
    |> validate_length(:title, min: 1, max: 500)
    |> validate_length(:author, min: 1, max: 500)
    |> validate_number(:year, greater_than: 0, less_than: 3000)
  end
end
