defmodule BookApi.Books.Book do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :binary_id, autogenerate: true}
  @foreign_key_type :binary_id
  schema "books" do
    field :title, :string
    field :author, :string
    field :year, :integer
    field :isbn, :string

    timestamps(type: :utc_datetime)
  end

  @doc false
  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
    |> validate_length(:title, min: 1, max: 255)
    |> validate_length(:author, min: 1, max: 255)
    |> validate_length(:isbn, max: 13)
    |> validate_number(:year, greater_than: 1000, less_than: 2100)
  end
end
