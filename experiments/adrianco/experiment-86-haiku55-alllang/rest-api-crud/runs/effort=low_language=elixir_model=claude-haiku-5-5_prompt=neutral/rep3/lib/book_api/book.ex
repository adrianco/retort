defmodule BookApi.Book do
  @moduledoc "Ecto schema and changeset for a book."
  use Ecto.Schema
  import Ecto.Changeset

  @type t :: %__MODULE__{}

  schema "books" do
    field(:title, :string)
    field(:author, :string)
    field(:year, :integer)
    field(:isbn, :string)

    timestamps(type: :utc_datetime)
  end

  @fields [:title, :author, :year, :isbn]

  def changeset(book, attrs) do
    book
    |> cast(attrs, @fields)
    |> validate_required([:title, :author], message: "is required")
    |> validate_length(:title, min: 1, max: 500)
    |> validate_length(:author, min: 1, max: 255)
    |> validate_number(:year, greater_than: 0, less_than_or_equal_to: 9999)
    |> validate_length(:isbn, max: 20)
  end
end
