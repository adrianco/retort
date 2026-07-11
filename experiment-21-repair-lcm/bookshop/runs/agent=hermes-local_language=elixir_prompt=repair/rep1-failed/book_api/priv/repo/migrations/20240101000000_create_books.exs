defmodule BookApi.Repo.Migrations.CreateBooks do
  use Ecto.Migration

  def change do
    create table(:books) do
      add :title, :string
      add :author, :string
      add :year, :integer
      add :isbn, :string

      timestamps()
    end
  end
end
