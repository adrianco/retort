defmodule BookApi.Application do
  use Application

  @impl true
  def start(_type, _args) do
    database = Application.get_env(:book_api, :database, "books.db")
    port = Application.get_env(:book_api, :port, 4000)

    children = [
      {BookApi.Store, database},
      {Plug.Cowboy, scheme: :http, plug: BookApi.Router, options: [port: port]}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
