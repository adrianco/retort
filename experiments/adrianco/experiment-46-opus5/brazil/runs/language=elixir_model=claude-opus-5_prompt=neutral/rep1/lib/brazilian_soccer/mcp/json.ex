defmodule BrazilianSoccer.MCP.JSON do
  @moduledoc """
  Makes query results JSON encodable.

  Query results are full of structs, atoms, dates and tuple pairs, none of
  which `Jason` can encode on its own.  `sanitize/1` walks a result and turns
  it into plain maps, lists and strings, so every tool can return structured
  content next to its text answer.
  """

  alias BrazilianSoccer.Model.Match

  @doc "Recursively convert a term into JSON-encodable data."
  @spec sanitize(term) :: term
  def sanitize(%Date{} = date), do: Date.to_iso8601(date)
  def sanitize(%Time{} = time), do: Time.to_iso8601(time)
  def sanitize(%DateTime{} = datetime), do: DateTime.to_iso8601(datetime)
  def sanitize(%NaiveDateTime{} = datetime), do: NaiveDateTime.to_iso8601(datetime)
  def sanitize(%MapSet{} = set), do: set |> MapSet.to_list() |> sanitize()

  def sanitize(%Match{} = match) do
    match
    |> Map.from_struct()
    |> Map.put(:result, Match.result(match))
    |> Map.put(:played, Match.played?(match))
    |> sanitize()
  end

  def sanitize(%_{} = struct), do: struct |> Map.from_struct() |> sanitize()

  def sanitize(map) when is_map(map) do
    Map.new(map, fn {key, value} -> {key_to_string(key), sanitize(value)} end)
  end

  def sanitize(list) when is_list(list), do: Enum.map(list, &sanitize/1)
  def sanitize(tuple) when is_tuple(tuple), do: tuple |> Tuple.to_list() |> sanitize()

  def sanitize(atom) when is_atom(atom) and not is_boolean(atom) and not is_nil(atom),
    do: Atom.to_string(atom)

  def sanitize(other), do: other

  defp key_to_string(key) when is_atom(key), do: Atom.to_string(key)
  defp key_to_string(key) when is_binary(key), do: key
  defp key_to_string(key), do: to_string(key)
end
