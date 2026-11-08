defmodule BookCollection.Application do
  use Application

  def start(_type, _args) do
    with {:ok, supervisor} <- Supervisor.start_link([BookCollection.Repo], strategy: :one_for_one, name: BookCollection.Supervisor) do
      BookCollection.Repo.query!("CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)")
      if Application.get_env(:book_collection, :start_server) do
        {:ok, _} = Supervisor.start_child(supervisor, {Bandit, plug: BookCollection.Router, port: Application.fetch_env!(:book_collection, :port)})
      end
      {:ok, supervisor}
    end
  end
end
