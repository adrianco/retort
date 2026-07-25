defmodule BookApi.Books.Book do
  @moduledoc """
  Ecto schema and changeset rules for a book.
  """

  use Ecto.Schema
  import Ecto.Changeset

  @derive {Jason.Encoder, only: [:id, :title, :author, :year, :isbn, :inserted_at, :updated_at]}

  # A year far enough ahead to allow for announced-but-unpublished titles.
  @max_year 2100

  schema "books" do
    field(:title, :string)
    field(:author, :string)
    field(:year, :integer)
    field(:isbn, :string)

    timestamps(type: :utc_datetime)
  end

  @doc """
  Builds a changeset for creating or updating a book.

  `title` and `author` are required; `year` and `isbn` are optional but
  validated when present.
  """
  def changeset(book, attrs) do
    book
    |> cast(attrs, [:title, :author, :year, :isbn])
    |> update_change(:title, &trim/1)
    |> update_change(:author, &trim/1)
    |> update_change(:isbn, &trim/1)
    |> validate_required([:title, :author])
    |> validate_length(:title, max: 255)
    |> validate_length(:author, max: 255)
    |> validate_number(:year, greater_than: 0, less_than_or_equal_to: @max_year)
    |> validate_isbn()
    |> unique_constraint(:isbn)
  end

  defp trim(value) when is_binary(value), do: String.trim(value)
  defp trim(value), do: value

  # ISBN-10 and ISBN-13 both allow hyphens/spaces as separators; ISBN-10 may end
  # in an "X" check digit. Empty strings are normalised to nil so that repeated
  # blank submissions don't collide on the unique index.
  defp validate_isbn(changeset) do
    case get_change(changeset, :isbn) do
      nil ->
        changeset

      "" ->
        put_change(changeset, :isbn, nil)

      isbn ->
        digits = String.replace(isbn, ~r/[\s-]/, "")

        if Regex.match?(~r/^(\d{9}[\dX]|\d{13})$/i, digits) do
          changeset
        else
          add_error(changeset, :isbn, "must be a valid ISBN-10 or ISBN-13")
        end
    end
  end
end
