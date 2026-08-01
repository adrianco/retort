defmodule BrazilianSoccer.Normalize do
  @moduledoc false
  @aliases %{
    "sport club corinthians paulista" => "corinthians",
    "sao paulo fc" => "sao paulo",
    "gremio fbpa" => "gremio",
    "clube de regatas do flamengo" => "flamengo"
  }

  def text(nil), do: ""

  def text(value) do
    value
    |> to_string()
    |> String.trim()
    |> :unicode.characters_to_nfd_binary()
    |> String.replace(~r/\p{Mn}/u, "")
    |> String.downcase()
  end

  def team(value) do
    clean =
      value |> text() |> String.replace(~r/\s*-\s*[a-z]{2}$/u, "") |> String.replace(~r/\s+/, " ")

    Map.get(@aliases, clean, clean)
  end

  def display_team(value),
    do: value |> to_string() |> String.replace(~r/\s*-\s*[A-Z]{2}$/, "") |> String.trim()

  def date!(%Date{} = date), do: date

  def date!(value) when is_binary(value) do
    value = String.trim(value)

    cond do
      Regex.match?(~r/^\d{4}-\d{2}-\d{2}/, value) ->
        Date.from_iso8601!(String.slice(value, 0, 10))

      Regex.match?(~r/^\d{2}\/\d{2}\/\d{4}$/, value) ->
        [d, m, y] = String.split(value, "/")
        Date.new!(String.to_integer(y), String.to_integer(m), String.to_integer(d))

      true ->
        raise ArgumentError, "unsupported date: #{inspect(value)}"
    end
  end
end
