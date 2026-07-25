defmodule BooksApi.Repo.Migrations.CreateBooks do
  use Ecto.Migration

  def change do
    create table(:books) do
      add :title, :string, null: false
      add :author, :string, null: false
      add :year, :integer
      add :isbn, :string

      timestamps()
    end

    create index(:books, [:author])
  end
end
