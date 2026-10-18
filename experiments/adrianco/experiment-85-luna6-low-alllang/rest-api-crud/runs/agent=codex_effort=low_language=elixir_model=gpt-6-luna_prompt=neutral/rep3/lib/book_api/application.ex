defmodule BookApi.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children = [{BookApi.Server, port: String.to_integer(System.get_env("PORT", "4000"))}]
    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end
end
