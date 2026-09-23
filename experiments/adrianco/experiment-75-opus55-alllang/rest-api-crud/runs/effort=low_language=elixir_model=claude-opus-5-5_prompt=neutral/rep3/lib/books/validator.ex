defmodule Books.Validator do
  @moduledoc "Validates and normalises book input params."

  def validate(params) when is_map(params) do
    errors =
      []
      |> required(params, "title")
      |> required(params, "author")
      |> check(params["year"] == nil or is_integer(params["year"]), "year", "must be an integer")
      |> check(params["isbn"] == nil or is_binary(params["isbn"]), "isbn", "must be a string")

    if errors == [] do
      {:ok, %{title: String.trim(params["title"]), author: String.trim(params["author"]), year: params["year"], isbn: params["isbn"]}}
    else
      {:error, Map.new(Enum.reverse(errors))}
    end
  end

  def validate(_), do: {:error, %{"body" => "must be a JSON object"}}

  defp required(errs, params, key) do
    case params[key] do
      v when is_binary(v) -> if String.trim(v) == "", do: [{key, "is required"} | errs], else: errs
      nil -> [{key, "is required"} | errs]
      _ -> [{key, "must be a string"} | errs]
    end
  end

  defp check(errs, true, _, _), do: errs
  defp check(errs, false, key, msg), do: [{key, msg} | errs]
end
