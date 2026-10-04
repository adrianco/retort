defmodule BrazilianSoccer.MCP.Server do
  @moduledoc """
  Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).

  Supports `initialize`, `ping`, `tools/list` and `tools/call`. `handle/1`
  is a pure function from a decoded request to a response map (or nil for
  notifications), which keeps the protocol testable without any I/O.
  """

  alias BrazilianSoccer.MCP.Tools

  @protocol_version "2024-11-05"
  @supported_versions ["2024-11-05", "2025-03-26", "2025-06-18"]

  @doc "Reads requests from `input` until EOF, writing responses to `output`."
  def run(input \\ :stdio, output \\ :stdio) do
    case IO.read(input, :line) do
      :eof ->
        :ok

      {:error, _} ->
        :ok

      line ->
        case handle_line(line) do
          nil -> :ok
          response -> IO.write(output, [response, "\n"])
        end

        run(input, output)
    end
  end

  @doc "Handles one raw JSON line; returns the encoded response or nil."
  def handle_line(line) do
    case String.trim(line) do
      "" ->
        nil

      json ->
        response =
          case JSON.decode(json) do
            {:ok, batch} when is_list(batch) and batch != [] ->
              case batch |> Enum.map(&handle/1) |> Enum.reject(&is_nil/1) do
                [] -> nil
                responses -> responses
              end

            {:ok, request} ->
              handle(request)

            {:error, _} ->
              error(nil, -32700, "Parse error")
          end

        response && JSON.encode!(response)
    end
  end

  @doc "Handles one decoded JSON-RPC message."
  def handle(%{"method" => method} = request) when is_binary(method) do
    id = request["id"]
    params = request["params"] || %{}

    if Map.has_key?(request, "id") do
      try do
        dispatch(method, params, id)
      rescue
        e -> error(id, -32603, "Internal error: " <> Exception.message(e))
      end
    else
      # Notifications (e.g. notifications/initialized) get no response.
      nil
    end
  end

  def handle(%{"id" => _, "result" => _}), do: nil
  def handle(%{"id" => _, "error" => _}), do: nil
  def handle(request) when is_map(request), do: error(request["id"], -32600, "Invalid Request")
  def handle(_), do: error(nil, -32600, "Invalid Request")

  defp dispatch("initialize", params, id) do
    requested = params["protocolVersion"]
    version = if requested in @supported_versions, do: requested, else: @protocol_version

    result(id, %{
      "protocolVersion" => version,
      "capabilities" => %{"tools" => %{"listChanged" => false}},
      "serverInfo" => %{"name" => "brazilian-soccer-mcp", "version" => "0.1.0"},
      "instructions" =>
        "Knowledge base of Brazilian soccer: Brasileirão (Série A 2003-2023, B and C), Copa do Brasil and Copa Libertadores matches plus the FIFA player database. Team names are normalised, so any common spelling works."
    })
  end

  defp dispatch("ping", _params, id), do: result(id, %{})
  defp dispatch("tools/list", _params, id), do: result(id, %{"tools" => Tools.list()})

  defp dispatch("tools/call", %{"name" => name} = params, id) when is_binary(name) do
    case Tools.call(name, params["arguments"] || %{}) do
      {:ok, text} ->
        result(id, %{"content" => [%{"type" => "text", "text" => text}], "isError" => false})

      {:error, message} ->
        result(id, %{"content" => [%{"type" => "text", "text" => message}], "isError" => true})
    end
  end

  defp dispatch("tools/call", _params, id),
    do: error(id, -32602, "Invalid params: missing tool name")

  defp dispatch(method, _params, id), do: error(id, -32601, "Method not found: #{method}")

  defp result(id, result), do: %{"jsonrpc" => "2.0", "id" => id, "result" => result}

  defp error(id, code, message),
    do: %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
end
