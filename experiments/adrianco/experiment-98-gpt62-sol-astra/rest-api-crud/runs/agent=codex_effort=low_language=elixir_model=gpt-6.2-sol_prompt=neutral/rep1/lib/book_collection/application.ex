defmodule BookCollection.Application do
  use Application

  @impl true
  def start(_type, _args) do
    database = Application.fetch_env!(:book_collection, :database)
    children = [{BookCollection.Store, database}]

    children =
      if Application.fetch_env!(:book_collection, :server) do
        port = Application.fetch_env!(:book_collection, :port)
        children ++ [{Bandit, plug: BookCollection.Router, port: port}]
      else
        children
      end

    Supervisor.start_link(children, strategy: :one_for_one, name: BookCollection.Supervisor)
  end
end
