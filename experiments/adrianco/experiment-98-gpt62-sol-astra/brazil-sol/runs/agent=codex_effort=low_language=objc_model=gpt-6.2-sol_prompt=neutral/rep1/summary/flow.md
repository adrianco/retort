# Flow

```mermaid
sequenceDiagram
    Client->>main.m: {"method":"tools/call","params":{"name":"find_matches","arguments":{...}}}
    main.m->>Soccer.m: call:@"find_matches" arguments:args
    Soccer.m->>Soccer.m: validate(args, inputSchema)
    Soccer.m->>Soccer.m: matching: (filter merged _matches by team/season/date/comp/stage)
    Soccer.m->>Soccer.m: page(@"matches", matches, args) + optional head_to_head
    Soccer.m-->>main.m: NSDictionary payload
    main.m->>main.m: NSJSONSerialization -> text; wrap as content[] + structuredContent
    main.m-->>Client: {"result":{"content":[...],"structuredContent":{...},"isError":false}}
```

On startup, `Soccer initWithDirectory:` reads all 5 match CSVs plus `fifa_data.csv` via the hand-written `readCSV()`, normalizes each team to a canonical `*_id` (`teamKey()` strips state suffixes, folds accents, applies aliases and regional disambiguation), then de-duplicates and merges records that describe the same fixture across files (calendar + detailed sources), inferring cup finals from closing legs. Queries then run entirely in memory.

Notable deviations from a naive implementation: results are paginated (`total` + `next_offset`), arguments are schema-validated server-side before dispatch, matches with missing scores are excluded from aggregates, and date inputs accept both ISO and DD/MM/YYYY. No persistence, no network, no external dependencies beyond Foundation.
