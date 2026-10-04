# ATDD findings

- 2026-10-03: Spec assumed Alisson is the top Brazilian GK; the FIFA data rates Ederson (86) above Alisson (85). Spec corrected to the data.
- 2026-10-03: Team-name normalisation merged Guarani (SP) with Guaraní (PAR) from Libertadores; foreign clubs now keep their country tag in their identity.
- 2026-10-03: BR-Football-Dataset labels a few non-Série-A matches as "Serie A" (e.g. Brasilia FC, CA Taguatinga in 2015), which corrupted relegation; standings now exclude clubs without a full fixture list.
- 2026-10-03: BR-Football-Dataset has only 377 of 380 matches for 2023 Série A, so the calculated 2023 table can differ from the real final table.
- 2026-10-03: Série A appears in three files (2003-2019, 2012-2022, 2014-2023); matches are merged per season + home + away so nothing is double-counted. The 2020 season ran into Feb 2021, so league dates in Jan-Mar count toward the previous season.
- 2026-10-03: Protocol driver launched a subprocess binary, so the suite exercised the system but reported 0% coverage. It now runs the MCP server in-process over pipes (same JSON-RPC interface). Added unit tests for the soccer and mcp packages.
