package main

import (
	"embed"
	"io/fs"
)

// embeddedData carries the six Kaggle CSV files inside the binary so the server
// can be launched from any working directory, which is how MCP clients start
// their servers. Pass -data to read the CSVs from disk instead.
//
//go:embed data/kaggle/*.csv
var embeddedData embed.FS

// embeddedDataFS returns a filesystem rooted at the directory containing the
// CSV files.
func embeddedDataFS() (fs.FS, error) {
	return fs.Sub(embeddedData, "data/kaggle")
}
