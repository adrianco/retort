defmodule BookApi.Application do
  # See https://hexdocs.pm/elixir/Application.html
  # for more information on OTP Applications
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      # Start the Ecto repository
      BookApi.Repo,
      # Start the Telemetry supervisor
      BookApiWeb.Telemetry,
      # Start the PubSub system
      {Phoenix.PubSub, name: BookApi.PubSub},
      # Start the Endpoint (http/https)
      BookApiWeb.Endpoint
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: BookApi.Supervisor]
    Supervisor.start_link(opts)
  end

  # Tell Phoenix to update the endpoint configuration
  # when the application is updated.
  @impl true
  def config_change(changed, _new, removed) do
    BookApiWeb.Endpoint.config_change(changed, removed)
    :ok
  end
end
