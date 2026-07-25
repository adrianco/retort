ExUnit.start()

# The graph is built once for the whole suite (a warm cache makes this a
# sub-second load); individual tests then read it for free.
{time, _} = :timer.tc(fn -> BrazilianSoccer.Repo.graph() end)
IO.puts("knowledge graph ready in #{div(time, 1000)}ms")
