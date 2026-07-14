defmodule BrasilSoccer.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    opts = [strategy: :one_for_one, name: BrasilSoccer.Supervisor]
    Supervisor.start_link(children(), opts)
  end

  # Preload the dataset under supervision everywhere except the test
  # environment, where suites inject their own fixture data.
  defp children do
    if Application.get_env(:brasil_soccer, :start_store, true) do
      [BrasilSoccer.Store]
    else
      []
    end
  end
end
