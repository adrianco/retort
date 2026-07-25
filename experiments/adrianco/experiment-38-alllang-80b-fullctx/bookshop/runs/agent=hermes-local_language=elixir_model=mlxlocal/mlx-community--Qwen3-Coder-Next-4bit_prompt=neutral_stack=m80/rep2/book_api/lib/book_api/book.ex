defmodule BookApi.Book do
  use Ecto.Schema
  import Ecto.Changeset

  @primary_key {:id, :integer, []}
  schema "books" do
    field :title, :string
    field :author, :string
    field :year, :integer
    field :isbn, :string

    timestamps(type: :utc_datetime, updated_at: false)
  end

  @doc false
  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
    |> validate_length(:title, min: 1, max: 255)
    |> validate_length(:author, min: 1, max: 255)
    |> validate_length(:isbn, min: 10, max: 20)
    |> validate_format(:isbn, ~r/^[0-9X-]+$/, message: "ISBN must contain only numbers, hyphens, or X")
  end
end
