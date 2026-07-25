defmodule BooksApi.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [BooksApi.Repo] ++ server_children()

    opts = [strategy: :one_for_one, name: BooksApi.Supervisor]
    Supervisor.start_link(children, opts)
  end

  defp server_children do
    if Application.get_env(:books_api, :server, true) do
      port = Application.get_env(:books_api, :port, 4000)
      [{Bandit, plug: BooksApi.Router, port: port}]
    else
      []
    end
  end
end
