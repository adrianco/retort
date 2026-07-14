defmodule BookApi.Application do
  use Application

  @impl true
  def start(_type, _args) do
    children =
      if Mix.env() == :test do
        [BookApi.Repo]
      else
        [
          BookApi.Repo,
          {Plug.Cowboy, scheme: :http, plug: BookApi.Router, options: [port: 4000]}
        ]
      end

    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
