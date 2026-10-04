defmodule BrazilianSoccer.Store do
  @moduledoc """
  Holds the loaded datasets in `:persistent_term` so every query reads them
  without copying. Data is loaded lazily on first access.

  The data directory is taken from the `BRAZILIAN_SOCCER_DATA_DIR`
  environment variable, the `:data_dir` application env, or `data/kaggle`
  relative to the current directory.
  """

  alias BrazilianSoccer.Loader

  @key {__MODULE__, :data}

  def data do
    case :persistent_term.get(@key, nil) do
      nil -> load()
      data -> data
    end
  end

  def matches, do: data().matches
  def players, do: data().players

  @doc "(Re)loads the datasets, optionally from an explicit directory."
  def load(dir \\ data_dir()) do
    :global.trans({@key, self()}, fn ->
      data = Loader.load(dir)
      :persistent_term.put(@key, data)
      data
    end)
  end

  def data_dir do
    System.get_env("BRAZILIAN_SOCCER_DATA_DIR") ||
      Application.get_env(:brazilian_soccer, :data_dir) ||
      Path.join(File.cwd!(), "data/kaggle")
  end
end
