defmodule BookAPI.Books.Book do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :id, autogenerate: true}
  @foreign_key_type :id

  schema "books" do
    field :author, :string
    field :isbn, :string
    field :title, :string
    field :year, :integer

    timestamps()
  end

  @doc false
  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
    |> validate_length(:title, min: 1, max: 255)
    |> validate_length(:author, min: 1, max: 255)
    |> validate_length(:isbn, min: 10, max: 20)
    |> validate_format(:isbn, ~r/^[0-9X\-]+$/i, message: "ISBN must contain only numbers, hyphens, or X")
  end
end
