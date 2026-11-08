defmodule Books.Application do
  use Application

  def start(_type, _args) do
    children =
      [Books.Store] ++
        if Application.fetch_env!(:books, :server) do
          [{Bandit, plug: Books.Router, port: Application.fetch_env!(:books, :port)}]
        else
          []
        end

    Supervisor.start_link(children, strategy: :one_for_one, name: Books.Supervisor)
  end
end
