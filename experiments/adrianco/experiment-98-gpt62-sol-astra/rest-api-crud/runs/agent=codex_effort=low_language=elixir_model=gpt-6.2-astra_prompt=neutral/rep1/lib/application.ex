defmodule Books.Application do
  use Application

  def start(_type, _args) do
    server =
      if Application.fetch_env!(:books, :serve) do
        [{Bandit, plug: Books.Router, port: String.to_integer(System.get_env("PORT", "4000"))}]
      else
        []
      end

    children = [{Books.Store, Application.fetch_env!(:books, :db_path)} | server]
    Supervisor.start_link(children, strategy: :one_for_one)
  end
end
