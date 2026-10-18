defmodule BookApi.Application do
  use Application

  def start(_type, _args) do
    port = String.to_integer(System.get_env("PORT", "4000"))
    db_path = System.get_env("DATABASE_PATH", "data/books.sqlite3")
    File.mkdir_p!(Path.dirname(db_path))

    children = [
      {BookApi.Store, db_path},
      {BookApi.Server, port}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
