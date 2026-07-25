defmodule BookApi.Book do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :id, autogenerate: true}
  schema "books" do
    field :title, :string
    field :author, :string
    field :year, :integer
    field :isbn, :string

    timestamps()
  end

  @doc false
  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
    |> validate_length(:title, min: 1, max: 255)
    |> validate_length(:author, min: 1, max: 255)
    |> validate_length(:isbn, max: 20)
    |> unique_constraint(:isbn, name: :books_isbn_index)
  end
end
