defmodule BookApi.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{BookApi.DB, path: Application.fetch_env!(:book_api, :database_path)}] ++ server_children()

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end

  defp server_children do
    if Application.get_env(:book_api, :start_server, true) do
      [{Bandit, plug: BookApi.Router, port: Application.get_env(:book_api, :port, 4000)}]
    else
      []
    end
  end
end
