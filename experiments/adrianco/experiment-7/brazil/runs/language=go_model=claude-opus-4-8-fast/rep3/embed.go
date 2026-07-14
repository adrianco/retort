// embed.go - compile-time embedding of the Kaggle datasets.
//
// Context
// -------
// The six CSV datasets are embedded into the binary with go:embed so the MCP
// server is fully self-contained and works regardless of the process working
// directory (MCP hosts often launch servers from arbitrary locations). The
// embed directive can only reference files at or below this file's directory,
// which is why this lives at the module root alongside data/.
//
// dataFS exposes the datasets rooted at the data/kaggle directory so the loader
// sees the bare CSV file names it expects.
package main

import (
	"embed"
	"io/fs"
)

//go:embed data/kaggle/*.csv
var embeddedData embed.FS

// dataFS returns the embedded datasets rooted so that the loader finds files by
// their bare names (e.g. "fifa_data.csv").
func dataFS() fs.FS {
	sub, err := fs.Sub(embeddedData, "data/kaggle")
	if err != nil {
		// Unreachable: the path is a compile-time constant matching the embed.
		panic(err)
	}
	return sub
}
