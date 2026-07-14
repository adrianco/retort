defmodule BrSoccer.Competition do
  @moduledoc "Competition identifiers, display names and free-text parsing."

  @names %{
    brasileirao: "Brasileirão Série A",
    serie_b: "Brasileirão Série B",
    serie_c: "Brasileirão Série C",
    copa_do_brasil: "Copa do Brasil",
    libertadores: "Copa Libertadores",
    other: "Other"
  }

  @doc "Human-readable name for a competition atom."
  def name(comp), do: Map.get(@names, comp, to_string(comp))

  @doc "All known competition atoms."
  def all, do: Map.keys(@names)

  @doc """
  Parse a free-text competition name into an atom, or `nil` if unrecognised.

  Accepts the canonical atoms and a range of human spellings/aliases.
  """
  def parse(nil), do: nil
  def parse(atom) when is_atom(atom), do: if(Map.has_key?(@names, atom), do: atom, else: nil)

  def parse(text) when is_binary(text) do
    t = text |> BrSoccer.TeamName.deaccent() |> String.downcase() |> String.trim()

    cond do
      t == "" -> nil
      t in ~w(brasileirao serie_a) -> :brasileirao
      String.contains?(t, "serie a") -> :brasileirao
      String.contains?(t, "brasileir") -> :brasileirao
      String.contains?(t, "serie b") or t == "serie_b" -> :serie_b
      String.contains?(t, "serie c") or t == "serie_c" -> :serie_c
      String.contains?(t, "libertadores") -> :libertadores
      String.contains?(t, "copa do brasil") or t in ~w(cup copa) -> :copa_do_brasil
      true -> nil
    end
  end
end
