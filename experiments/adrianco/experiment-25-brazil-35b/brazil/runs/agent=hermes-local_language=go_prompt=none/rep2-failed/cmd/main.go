package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/pkg/loader"
	"brazilian-soccer-mcp/pkg/server"
)

func main() {
	// Determine base directory
	baseDir, err := findBaseDir()
	if err != nil {
		log.Fatalf("Error: %v", err)
	}
	fmt.Printf("Using data from: %s\n", baseDir)

	dataMgr := loader.NewManager()
	loadAll(dataMgr, baseDir)

	mcpSrv := server.New(dataMgr, "file://"+filepath.Join(baseDir, "data"))

	fmt.Printf("Loaded %d matches, %d players\n", dataMgr.TotalMatchCount(), dataMgr.TotalPlayerCount())
	fmt.Println("Starting Brazilian Soccer MCP Server on stdio...")

	if err := server.ServeStdio(mcpSrv.Server()); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}

func findBaseDir() (string, error) {
	// Check from current directory
	cwd, err := os.Getwd()
	if err == nil {
		if _, err := os.Stat(filepath.Join(cwd, "data", "kaggle")); err == nil {
			return cwd, nil
		}
	}
	// Check common patterns
	for _, rel := range []string{"data/kaggle", "../data/kaggle", "../../data/kaggle"} {
		if info, err := os.Stat(rel); err == nil && info.IsDir() {
			abs, _ := filepath.Abs(rel)
			return abs, nil
		}
	}
	return "", fmt.Errorf("cannot find data/kaggle directory")
}

func loadAll(m *loader.Manager, baseDir string) {
	dataDir := filepath.Join(baseDir, "data", "kaggle")
	loads := []struct {
		name   string
		path   string
		fn     func(*loader.Manager, string) error
	}{
		{"Brasileirao", filepath.Join(dataDir, "Brasileirao_Matches.csv"), m.LoadBrasileirao},
		{"Brazilian Cup", filepath.Join(dataDir, "Brazilian_Cup_Matches.csv"), m.LoadBrazilianCup},
		{"Libertadores", filepath.Join(dataDir, "Libertadores_Matches.csv"), m.LoadLibertadores},
		{"BR Football", filepath.Join(dataDir, "BR-Football-Dataset.csv"), m.LoadBRFootball},
		{"Novo Campeonato", filepath.Join(dataDir, "novo_campeonato_brasileiro.csv"), m.LoadNovoCampeonato},
	}
	for _, l := range loads {
		if _, err := os.Stat(l.path); err == nil {
			fmt.Printf("  Loading %s... ", l.name)
			if err := l.fn(m, l.path); err != nil {
				fmt.Printf("ERROR: %v\n", err)
			} else {
				fmt.Println("OK")
			}
		} else {
			fmt.Printf("  Skipping %s (not found)\n", l.name)
		}
	}
	// Players
	ppath := filepath.Join(dataDir, "fifa_data.csv")
	if _, err := os.Stat(ppath); err == nil {
		fmt.Printf("  Loading FIFA players... ")
		if err := m.LoadPlayers(ppath); err != nil {
			fmt.Printf("ERROR: %v\n", err)
		} else {
			fmt.Printf("OK (%d players)\n", m.TotalPlayerCount())
		}
	} else {
		fmt.Println("  Skipping FIFA players (not found)")
	}
}
