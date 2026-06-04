defmodule BookApi.Book do
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

  @required_fields [:title, :author]
  @optional_fields [:year, :isbn]

  def changeset(book, attrs) do
    book
    |> cast(attrs, @required_fields ++ @optional_fields)
    |> validate_required(@required_fields, message: "can't be blank")
    |> validate_length(:title, min: 1, max: 500)
    |> validate_length(:author, min: 1, max: 500)
    |> validate_number(:year, greater_than: -10_000, less_than: 10_000)
  end
end
