defmodule BooksApi.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    port = Application.get_env(:books_api, :port)

    children = [
      BooksApi.Repo,
      {Bandit, plug: BooksApi.Router, port: port}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: BooksApi.Supervisor)
  end
end
