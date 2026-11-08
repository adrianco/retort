defmodule BookCollection.Book do
  use Ecto.Schema
  import Ecto.Changeset

  schema "books" do
    field :title, :string
    field :author, :string
    field :year, :integer
    field :isbn, :string
  end

  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> validate_required([:title, :author])
  end

  def json(book), do: Map.take(book, [:id, :title, :author, :year, :isbn])
end
