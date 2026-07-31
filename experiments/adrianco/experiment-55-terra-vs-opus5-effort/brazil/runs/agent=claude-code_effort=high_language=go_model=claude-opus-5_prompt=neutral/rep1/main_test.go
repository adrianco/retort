// main_test.go covers the command layer: that the datasets embedded in the
// binary are complete and load identically to the ones on disk, and that the
// -demo and -ask modes work through the real MCP client/server round trip.
package main

import (
	"bytes"
	"context"
	"io/fs"
	"os"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpsrv"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func TestEmbeddedDatasetsAreComplete(t *testing.T) {
	fsys, err := embeddedDataFS()
	if err != nil {
		t.Fatalf("embeddedDataFS: %v", err)
	}
	for _, name := range soccer.SourceFiles {
		info, err := fs.Stat(fsys, name)
		if err != nil {
			t.Fatalf("%s is not embedded: %v", name, err)
		}
		if info.Size() == 0 {
			t.Errorf("%s is embedded but empty", name)
		}
	}
}

func TestEmbeddedAndOnDiskDataAgree(t *testing.T) {
	embedded, err := embeddedDataFS()
	if err != nil {
		t.Fatalf("embeddedDataFS: %v", err)
	}
	fromEmbed, err := soccer.Load(embedded)
	if err != nil {
		t.Fatalf("loading embedded data: %v", err)
	}
	fromDisk, err := soccer.Load(os.DirFS("data/kaggle"))
	if err != nil {
		t.Fatalf("loading on-disk data: %v", err)
	}
	if len(fromEmbed.Matches) != len(fromDisk.Matches) ||
		len(fromEmbed.Teams) != len(fromDisk.Teams) ||
		len(fromEmbed.Players) != len(fromDisk.Players) {
		t.Errorf("embedded graph (%d/%d/%d) differs from on-disk graph (%d/%d/%d)",
			len(fromEmbed.Teams), len(fromEmbed.Matches), len(fromEmbed.Players),
			len(fromDisk.Teams), len(fromDisk.Matches), len(fromDisk.Players))
	}
}

func TestDemoAnswersEveryQuestion(t *testing.T) {
	g, err := soccer.Load(os.DirFS("data/kaggle"))
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	var buf bytes.Buffer
	if err := runDemo(context.Background(), mcpsrv.New(g), &buf); err != nil {
		t.Fatalf("runDemo: %v", err)
	}
	out := buf.String()
	for _, q := range mcpsrv.SampleQuestions() {
		if !strings.Contains(out, q.Question) {
			t.Errorf("demo output is missing %q", q.Question)
		}
	}
	if !strings.Contains(out, "sample questions answered") {
		t.Error("demo did not run to completion")
	}
}

func TestAskMode(t *testing.T) {
	g, err := soccer.Load(os.DirFS("data/kaggle"))
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	srv := mcpsrv.New(g)

	var buf bytes.Buffer
	if err := runAsk(context.Background(), srv, "standings", `{"competition":"serie-a","season":2019}`, &buf); err != nil {
		t.Fatalf("runAsk: %v", err)
	}
	if !strings.Contains(buf.String(), "Champion: Flamengo") {
		t.Errorf("unexpected answer:\n%s", buf.String())
	}

	buf.Reset()
	if err := runAsk(context.Background(), srv, "standings", `not json`, &buf); err == nil {
		t.Error("expected malformed -args to be rejected")
	}
}
