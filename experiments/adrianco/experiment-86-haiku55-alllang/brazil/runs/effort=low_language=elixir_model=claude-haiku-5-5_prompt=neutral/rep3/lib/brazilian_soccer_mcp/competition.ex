defmodule BrazilianSoccerMcp.Competition do
  @moduledoc """
  Canonical competition keys, user-facing aliases and display labels.

  Keys are what the data loader stores on each match. `canonical/1` accepts
  either a key or a friendly name such as `"Copa do Brasil"` or `"Serie A"`.
  """

  alias BrazilianSoccerMcp.TeamName

  @labels %{
    "brasileirao" => "Brasileirão Série A",
    "brasileirao_b" => "Brasileirão Série B",
    "brasileirao_c" => "Brasileirão Série C",
    "copa_do_brasil" => "Copa do Brasil",
    "libertadores" => "Copa Libertadores"
  }

  @aliases %{
    "serie_a" => "brasileirao",
    "brasileirao_serie_a" => "brasileirao",
    "serie_b" => "brasileirao_b",
    "brasileirao_serie_b" => "brasileirao_b",
    "serie_c" => "brasileirao_c",
    "brasileirao_serie_c" => "brasileirao_c",
    "copa_libertadores" => "libertadores",
    "libertadores_da_america" => "libertadores"
  }

  @doc "Maps a key or friendly name to its canonical key. `nil` stays `nil`."
  @spec canonical(binary() | nil) :: binary() | nil
  def canonical(nil), do: nil

  def canonical(name) when is_binary(name) do
    key = name |> TeamName.normalize() |> String.replace(" ", "_")
    Map.get(@aliases, key, key)
  end

  @doc "Display label for a canonical key. Unknown keys are returned unchanged."
  @spec label(binary() | nil) :: binary() | nil
  def label(key), do: Map.get(@labels, key, key)
end
