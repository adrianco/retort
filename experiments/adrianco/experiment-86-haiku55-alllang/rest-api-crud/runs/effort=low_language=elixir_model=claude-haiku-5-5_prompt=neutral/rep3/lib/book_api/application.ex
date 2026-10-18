defmodule BookApi.Application do
  @moduledoc false
  use Application

  @impl true
  def start(_type, _args) do
    children =
      [BookApi.Repo] ++
        if Application.get_env(:book_api, :start_server, true) do
          [{Plug.Cowboy, scheme: :http, plug: BookApi.Web.Router, options: [port: port()]}]
        else
          []
        end

    Supervisor.start_link(children, strategy: :one_for_one, name: BookApi.Supervisor)
  end

  defp port, do: Application.get_env(:book_api, :http_port, 4000)
end
