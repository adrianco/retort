defmodule Books.Application do
  use Application

  def start(_type, _args) do
    children = [Books.Repo]
    result = Supervisor.start_link(children, strategy: :one_for_one, name: Books.Supervisor)

    case result do
      {:ok, supervisor} ->
        Books.Repo.query!(
          "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL, year INTEGER, isbn TEXT)"
        )

        if Application.fetch_env!(:books, :start_server) do
          {:ok, _} =
            Supervisor.start_child(
              supervisor,
              {Bandit, plug: Books.Router, port: Application.fetch_env!(:books, :port)}
            )
        end

      _ ->
        :ok
    end

    result
  end
end
