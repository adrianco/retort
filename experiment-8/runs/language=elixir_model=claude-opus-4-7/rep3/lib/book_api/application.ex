defmodule BookApi.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children =
      [BookApi.Repo] ++ server_children()

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(children, opts)
  end

  defp server_children do
    if Application.get_env(:book_api, :start_server, true) do
      port = Application.get_env(:book_api, :port, 4000)
      [{Bandit, plug: BookApi.Router, port: port}]
    else
      []
    end
  end
end
