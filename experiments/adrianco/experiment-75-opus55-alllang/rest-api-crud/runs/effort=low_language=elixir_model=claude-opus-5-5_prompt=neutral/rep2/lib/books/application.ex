defmodule Books.Application do
  use Application

  def start(_type, _args) do
    server =
      if Application.get_env(:books, :server),
        do: [{Plug.Cowboy, scheme: :http, plug: Books.Router, options: [port: Application.get_env(:books, :port)]}],
        else: []

    children = [{Books.Repo, Application.get_env(:books, :db_path)} | server]
    Supervisor.start_link(children, strategy: :one_for_one, name: Books.Supervisor)
  end
end
