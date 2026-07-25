defmodule BookApiWeb.Telemetry do
  use Supervisor
  import Telemetry.Metrics

  def start_link(arg) do
    Supervisor.start_link(__MODULE__, arg, name: __MODULE__)
  end

  @impl true
  def init(_arg) do
    children = [
      # Telemetry poller will execute the given period measurements
      # every 10_000ms. Learn more here: https://hexdocs.pm/telemetry_metrics
      {:telemetry_poller, measurements: periodic_measurements(), period: 10_000}
    ]

    # See https://hexdocs.pm/elixir/Supervisor.html
    # for other strategies and supported options
    opts = [strategy: :one_for_one, name: BookApiWeb.Telemetry.Supervisor]
    Supervisor.init(children, opts)
  end

  defp periodic_measurements do
    [
      # A metric, which reports the number of processes that are currently alive
      {:process_count, [], :gauge},

      # A metric, which reports the number of bytes being used by the EVM
      {:process_memory, [:total], :gauge}
    ]
  end
end
