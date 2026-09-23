defmodule Books.Application do
  use Application

  @impl true
  def start(_type, _args) do
    server =
      if Application.get_env(:books, :server, true),
        do: [{Bandit, plug: Books.Router, port: Application.get_env(:books, :port, 4000)}],
        else: []

    children = [{Books.Repo, Application.get_env(:books, :db_path, "books.db")} | server]
    Supervisor.start_link(children, strategy: :one_for_one, name: Books.Supervisor)
  end
end
