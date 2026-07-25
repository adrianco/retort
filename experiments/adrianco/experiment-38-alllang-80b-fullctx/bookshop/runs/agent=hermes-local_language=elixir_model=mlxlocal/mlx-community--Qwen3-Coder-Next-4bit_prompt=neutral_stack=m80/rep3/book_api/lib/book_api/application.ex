defmodule BookAPI.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Start the Ecto repository
      BookAPI.Repo,
      # Start the endpoint
      {Plug.Cowboy, 
        scheme: :http, 
        plug: BookAPIWeb.Router,
        options: [port: 4000]}
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: BookAPI.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
