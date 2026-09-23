defmodule Books.Application do
  use Application

  @impl true
  def start(_type, _args) do
    server =
      if Application.get_env(:books, :server),
        do: [{Bandit, plug: Books.Router, port: Application.get_env(:books, :port)}],
        else: []

    children = [{Books.Repo, Application.get_env(:books, :db_path)} | server]
    Supervisor.start_link(children, strategy: :one_for_one, name: Books.Supervisor)
  end
end
