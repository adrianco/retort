defmodule BookApi.Book do
  @moduledoc """
  Ecto schema and changeset for a book.
  """
  use Ecto.Schema
  import Ecto.Changeset

  @derive {Jason.Encoder, only: [:id, :title, :author, :year, :isbn, :inserted_at, :updated_at]}
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
    |> validate_number(:year, greater_than: 0, less_than_or_equal_to: 9999)
  end
end
