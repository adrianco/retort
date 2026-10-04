defmodule BookApi.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{BookApi.Store, path: Application.fetch_env!(:book_api, :db_path)}] ++
        if Application.get_env(:book_api, :server, true) do
          [{Bandit, plug: BookApi.Router, port: Application.fetch_env!(:book_api, :port)}]
        else
          []
        end

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
