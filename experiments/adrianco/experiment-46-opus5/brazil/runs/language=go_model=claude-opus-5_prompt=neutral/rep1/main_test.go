// main_test.go - BDD scenarios for the command line entry points.
//
// Context
//
//	The stdio server itself is exercised through the in-memory transport in
//	internal/mcpserver. What is left to prove here is that the process wiring
//	works: that the dataset directory is discovered without configuration, that
//	-check and -list-tools succeed, that -tool performs a real MCP round trip,
//	and that a bad tool name or malformed JSON fails loudly rather than
//	silently.
package main

import (
	"context"
	"errors"
	"io"
	"os"
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/bdd"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// captureStdout runs fn with stdout redirected and returns what it wrote.
func captureStdout(t *testing.T, fn func() error) (string, error) {
	t.Helper()
	orig := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe: %v", err)
	}
	os.Stdout = w

	done := make(chan string, 1)
	go func() {
		var b strings.Builder
		buf := make([]byte, 4096)
		for {
			n, err := r.Read(buf)
			if n > 0 {
				b.Write(buf[:n])
			}
			if err != nil {
				break
			}
		}
		done <- b.String()
	}()

	runErr := fn()
	w.Close()
	os.Stdout = orig
	return <-done, runErr
}

func TestFeatureCommandLine(t *testing.T) {
	bdd.Feature(t, "Command line entry points")

	bdd.Scenario(t, "the dataset directory is discovered without configuration", func(s *bdd.S) {
		var out string
		var err error
		s.Given("no -data flag and no environment variable", nil)
		s.When("-check runs", func() {
			out, err = captureStdout(s.T, func() error {
				return run(options{check: true, quiet: true, args: "{}"})
			})
		})
		s.Then("the datasets load and a report is printed", func() {
			if err != nil {
				s.Fatalf("run: %v", err)
			}
			for _, want := range []string{"Clubs:", "Matches:", "Players:", "Brasileirao_Matches.csv", "Copa Libertadores"} {
				if !strings.Contains(out, want) {
					s.Errorf("report is missing %q; got:\n%s", want, out)
				}
			}
		})
	})

	bdd.Scenario(t, "a missing dataset directory fails with a clear message", func(s *bdd.S) {
		var err error
		s.Given("a -data path that does not hold the CSV files", nil)
		s.When("the server starts", func() {
			err = run(options{dataDir: filepathJoin(s.TempDir(), "nope"), check: true, quiet: true, args: "{}"})
		})
		s.Then("the error names the directory", func() {
			if err == nil {
				s.Fatal("expected an error")
			}
			if !strings.Contains(err.Error(), "nope") {
				s.Errorf("error %q does not name the directory", err)
			}
		})
	})

	bdd.Scenario(t, "-list-tools prints every tool", func(s *bdd.S) {
		var out string
		var err error
		s.Given("the loaded server", nil)
		s.When("-list-tools runs", func() {
			out, err = captureStdout(s.T, func() error {
				return run(options{listTools: true, quiet: true, args: "{}"})
			})
		})
		s.Then("18 tools are listed with descriptions", func() {
			if err != nil {
				s.Fatalf("run: %v", err)
			}
			if !strings.Contains(out, "18 tools") {
				s.Errorf("output does not report the tool count:\n%s", out)
			}
			for _, want := range []string{"find_matches", "head_to_head", "competition_standings", "search_players"} {
				if !strings.Contains(out, want) {
					s.Errorf("tool %s is missing from the listing", want)
				}
			}
		})
	})

	bdd.Scenario(t, "-tool performs a real MCP round trip", func(s *bdd.S) {
		var out string
		var err error
		s.Given("the loaded server", nil)
		s.When("a head_to_head call is made from the command line", func() {
			out, err = captureStdout(s.T, func() error {
				return run(options{
					quiet: true,
					tool:  "head_to_head",
					args:  `{"team_a":"Gremio","team_b":"Internacional","limit":3}`,
				})
			})
		})
		s.Then("the Gre-Nal answer is printed", func() {
			if err != nil {
				s.Fatalf("run: %v", err)
			}
			for _, want := range []string{"Gre-Nal", "Grêmio", "Internacional", "Head-to-head in dataset"} {
				if !strings.Contains(out, want) {
					s.Errorf("output is missing %q; got:\n%s", want, out)
				}
			}
		})
	})

	bdd.Scenario(t, "bad command line input is reported", func(s *bdd.S) {
		s.Given("the loaded server", nil)
		s.Then("malformed -args JSON is rejected", func() {
			err := run(options{quiet: true, tool: "graph_summary", args: "{not json"})
			if err == nil || !strings.Contains(err.Error(), "JSON") {
				s.Errorf("error = %v, want a JSON parse failure", err)
			}
		})
		s.And("an unknown tool name is rejected", func() {
			_, err := captureStdout(s.T, func() error {
				return run(options{quiet: true, tool: "no_such_tool", args: "{}"})
			})
			if err == nil {
				s.Error("expected an error for an unknown tool")
			}
		})
		s.And("a tool level failure is surfaced as an error", func() {
			_, err := captureStdout(s.T, func() error {
				return run(options{quiet: true, tool: "team_stats", args: `{"team":"Real Madrid"}`})
			})
			if err == nil {
				s.Error("expected the tool error to propagate to the exit status")
			}
		})
	})
}

func TestFeatureShutdown(t *testing.T) {
	bdd.Feature(t, "Shutdown behaviour")

	bdd.Scenario(t, "a host that closes the pipe is not treated as a crash", func(s *bdd.S) {
		var runErr error
		s.Given("a server serving MCP over a pipe", nil)
		s.When("the host closes its end immediately", func() {
			dir, err := soccer.FindDataDir()
			if err != nil {
				s.Fatalf("FindDataDir: %v", err)
			}
			g, err := soccer.Load(dir)
			if err != nil {
				s.Fatalf("Load: %v", err)
			}
			r, w := io.Pipe()
			w.Close() // the reader now returns EOF straight away
			runErr = mcpserver.New(g).Run(context.Background(), &mcp.IOTransport{
				Reader: r, Writer: nopWriteCloser{io.Discard},
			})
		})
		s.Then("the server reports a clean shutdown so the exit status stays zero", func() {
			if !isCleanShutdown(runErr) {
				s.Errorf("Run returned %v, which would exit non-zero", runErr)
			}
		})
		s.And("a genuine failure is still reported", func() {
			if isCleanShutdown(errors.New("disk on fire")) {
				s.Error("a real error was misclassified as a clean shutdown")
			}
		})
	})
}

type nopWriteCloser struct{ io.Writer }

func (nopWriteCloser) Close() error { return nil }

// filepathJoin avoids importing path/filepath for a single call.
func filepathJoin(dir, name string) string {
	return dir + string(os.PathSeparator) + name
}
