defmodule BrazilianSoccerMcp.StdioRunner do
  @moduledoc """
  Production MCP transport: reads JSON-RPC requests from stdin,
  writes JSON-RPC responses to stdout (newline-delimited).

  Start with: mix run --no-halt -e "BrazilianSoccerMcp.StdioRunner.start()"
  Or via escript/release.
  """

  alias BrazilianSoccerMcp.Server

  def start do
    Application.ensure_all_started(:brazilian_soccer_mcp)
    loop()
  end

  defp loop do
    case IO.gets("") do
      :eof ->
        :ok

      {:error, _reason} ->
        :ok

      line ->
        line = String.trim(line)

        if line != "" do
          case Jason.decode(line) do
            {:ok, request} ->
              case Server.handle_request(request) do
                {:ok, nil} ->
                  :ok

                {:ok, response} ->
                  IO.puts(Jason.encode!(response))
              end

            {:error, _} ->
              IO.puts(
                Jason.encode!(%{
                  "jsonrpc" => "2.0",
                  "id" => nil,
                  "error" => %{"code" => -32_700, "message" => "Parse error"}
                })
              )
          end
        end

        loop()
    end
  end
end
