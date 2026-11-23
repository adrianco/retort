defmodule Soccer.CSV do
  @moduledoc false

  def read!(path) do
    delimiters = :binary.compile_pattern([",", "\r", "\n"])

    [header | rows] =
      path |> File.read!() |> String.replace_prefix("\uFEFF", "") |> rows(delimiters, [], [])

    Enum.map(rows, fn row ->
      if length(row) != length(header), do: raise(ArgumentError, "Invalid CSV row in #{path}")
      Map.new(Enum.zip(header, row))
    end)
  end

  defp rows("", _, [], result), do: Enum.reverse(result)

  defp rows(input, delimiters, fields, result) do
    {value, rest} = field(input, delimiters)
    fields = [value | fields]

    case rest do
      <<?,, tail::binary>> -> rows(tail, delimiters, fields, result)
      <<"\r\n", tail::binary>> -> rows(tail, delimiters, [], [Enum.reverse(fields) | result])
      <<"\n", tail::binary>> -> rows(tail, delimiters, [], [Enum.reverse(fields) | result])
      "" -> Enum.reverse([Enum.reverse(fields) | result])
      _ -> raise ArgumentError, "Invalid CSV field terminator"
    end
  end

  defp field(<<?", rest::binary>>, _), do: quoted(rest, [])

  defp field(input, delimiters) do
    case :binary.match(input, delimiters) do
      :nomatch -> {input, ""}
      {offset, _} -> :erlang.split_binary(input, offset)
    end
  end

  defp quoted(input, parts) do
    case :binary.match(input, "\"") do
      {offset, 1} ->
        <<part::binary-size(^offset), ?", rest::binary>> = input

        case rest do
          <<?", tail::binary>> -> quoted(tail, ["\"", part | parts])
          _ -> {IO.iodata_to_binary(Enum.reverse([part | parts])), rest}
        end

      :nomatch ->
        raise ArgumentError, "Unterminated CSV quote"
    end
  end
end
