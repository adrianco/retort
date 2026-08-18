defmodule BrazilianSoccerMcp.Store do
  use GenServer
  alias BrazilianSoccerMcp.Catalog
  def start_link(_opts), do: GenServer.start_link(__MODULE__, nil, name: __MODULE__)
  def catalog, do: GenServer.call(__MODULE__, :catalog, :infinity)

  def init(_) do
    data_dir =
      Application.get_env(
        :brazilian_soccer_mcp,
        :data_dir,
        Path.expand("data/kaggle", File.cwd!())
      )

    {:ok, {:unloaded, data_dir}}
  end

  def handle_call(:catalog, _from, {:loaded, catalog}),
    do: {:reply, {:ok, catalog}, {:loaded, catalog}}

  def handle_call(:catalog, _from, {:unloaded, dir}) do
    result = Catalog.load(dir)

    {:reply, result,
     case result do
       {:ok, catalog} -> {:loaded, catalog}
       _ -> {:unloaded, dir}
     end}
  end
end
