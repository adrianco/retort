defmodule BookApi.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [{BookApi.Store, database: Application.fetch_env!(:book_api, :database)}] ++
        if Application.fetch_env!(:book_api, :server) do
          [{Bandit, plug: BookApi.Router, port: Application.fetch_env!(:book_api, :port)}]
        else
          []
        end

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
