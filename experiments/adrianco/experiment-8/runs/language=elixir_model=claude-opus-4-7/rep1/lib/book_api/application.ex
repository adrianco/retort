defmodule BookApi.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    port = Application.get_env(:book_api, :port, 4000)
    db_path = Application.get_env(:book_api, :db_path, "books.db")

    children = [
      {BookApi.Repo, db_path: db_path},
      {Plug.Cowboy, scheme: :http, plug: BookApi.Router, options: [port: port]}
    ]

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
