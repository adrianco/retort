defmodule BrazilianSoccer.MCP.Server do
  @moduledoc "MCP protocol handler for Brazilian Soccer data."

  alias BrazilianSoccer.MCP.Tools

  @protocol_version "2024-11-05"
  @server_info %{"name" => "brazilian-soccer-mcp", "version" => "1.0.0"}

  def handle_request(%{"method" => "initialize", "id" => id} = _req) do
    ok(id, %{
      "protocolVersion" => @protocol_version,
      "capabilities" => %{"tools" => %{}},
      "serverInfo" => @server_info
    })
  end

  def handle_request(%{"method" => "notifications/initialized"}) do
    nil
  end

  def handle_request(%{"method" => "tools/list", "id" => id}) do
    ok(id, %{"tools" => Tools.definitions()})
  end

  def handle_request(%{"method" => "tools/call", "id" => id, "params" => params}) do
    tool_name = params["name"]
    args = params["arguments"] || %{}

    case Tools.call(tool_name, args) do
      {:ok, text} ->
        ok(id, %{"content" => [%{"type" => "text", "text" => text}]})

      {:error, reason} ->
        error(id, -32602, reason)
    end
  end

  def handle_request(%{"id" => id, "method" => method}) do
    error(id, -32601, "Method not found: #{method}")
  end

  def handle_request(_), do: nil

  def run do
    :io.setopts(:standard_io, encoding: :utf8)
    loop()
  end

  defp loop do
    case IO.read(:line) do
      :eof ->
        :ok

      {:error, _reason} ->
        :ok

      line ->
        line = String.trim(line)

        if line != "" do
          case Jason.decode(line) do
            {:ok, request} ->
              case handle_request(request) do
                nil -> :ok
                response -> IO.puts(Jason.encode!(response))
              end

            {:error, _} ->
              IO.puts(Jason.encode!(error(nil, -32700, "Parse error")))
          end
        end

        loop()
    end
  end

  defp ok(id, result) do
    %{"jsonrpc" => "2.0", "id" => id, "result" => result}
  end

  defp error(id, code, message) do
    %{"jsonrpc" => "2.0", "id" => id, "error" => %{"code" => code, "message" => message}}
  end
end
