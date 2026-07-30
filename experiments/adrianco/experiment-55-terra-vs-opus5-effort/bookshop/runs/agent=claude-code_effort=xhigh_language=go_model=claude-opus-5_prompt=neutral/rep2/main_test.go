package main

import (
	"context"
	"errors"
	"flag"
	"io"
	"log/slog"
	"net"
	"net/http"
	"testing"
	"time"
)

func TestParseConfigDefaults(t *testing.T) {
	// Clear the environment this test's defaults would otherwise inherit.
	for _, key := range []string{"PORT", "BOOKAPI_ADDR", "BOOKAPI_DB", "BOOKAPI_LOG_FORMAT"} {
		t.Setenv(key, "")
	}

	cfg, err := parseConfig(nil, io.Discard)
	if err != nil {
		t.Fatalf("parseConfig: %v", err)
	}
	if cfg.addr != ":8080" {
		t.Errorf("addr = %q, want \":8080\"", cfg.addr)
	}
	if cfg.dbPath != "books.db" {
		t.Errorf("dbPath = %q, want \"books.db\"", cfg.dbPath)
	}
	if cfg.logFmt != "text" {
		t.Errorf("logFmt = %q, want \"text\"", cfg.logFmt)
	}
}

func TestParseConfigPrecedence(t *testing.T) {
	t.Run("PORT sets the listen port", func(t *testing.T) {
		t.Setenv("PORT", "9000")
		t.Setenv("BOOKAPI_ADDR", "")

		cfg, err := parseConfig(nil, io.Discard)
		if err != nil {
			t.Fatalf("parseConfig: %v", err)
		}
		if cfg.addr != ":9000" {
			t.Errorf("addr = %q, want \":9000\"", cfg.addr)
		}
	})

	t.Run("BOOKAPI_ADDR beats PORT", func(t *testing.T) {
		t.Setenv("PORT", "9000")
		t.Setenv("BOOKAPI_ADDR", "127.0.0.1:9100")

		cfg, err := parseConfig(nil, io.Discard)
		if err != nil {
			t.Fatalf("parseConfig: %v", err)
		}
		if cfg.addr != "127.0.0.1:9100" {
			t.Errorf("addr = %q, want \"127.0.0.1:9100\"", cfg.addr)
		}
	})

	t.Run("flags beat the environment", func(t *testing.T) {
		t.Setenv("PORT", "9000")
		t.Setenv("BOOKAPI_ADDR", "127.0.0.1:9100")
		t.Setenv("BOOKAPI_DB", "from-env.db")

		cfg, err := parseConfig([]string{"-addr", "127.0.0.1:9200", "-db", "from-flag.db", "-log-format", "json"}, io.Discard)
		if err != nil {
			t.Fatalf("parseConfig: %v", err)
		}
		if cfg.addr != "127.0.0.1:9200" {
			t.Errorf("addr = %q, want \"127.0.0.1:9200\"", cfg.addr)
		}
		if cfg.dbPath != "from-flag.db" {
			t.Errorf("dbPath = %q, want \"from-flag.db\"", cfg.dbPath)
		}
		if cfg.logFmt != "json" {
			t.Errorf("logFmt = %q, want \"json\"", cfg.logFmt)
		}
	})
}

// main distinguishes the three ways a command line can fail, so the errors
// have to stay distinguishable.
func TestParseConfigRejectsBadInput(t *testing.T) {
	// -h is a request for the usage text, not a failure.
	if _, err := parseConfig([]string{"-h"}, io.Discard); !errors.Is(err, flag.ErrHelp) {
		t.Errorf("parseConfig(-h) error = %v, want flag.ErrHelp", err)
	}

	// An unknown flag: the flag package has already printed the usage text,
	// so main must not report it again.
	if _, err := parseConfig([]string{"-nonsense"}, io.Discard); !errors.Is(err, errUsage) {
		t.Errorf("parseConfig(-nonsense) error = %v, want it to wrap errUsage", err)
	}

	// A value this program rejects itself: nothing has been printed yet, so
	// this one is main's to report.
	_, err := parseConfig([]string{"-log-format", "yaml"}, io.Discard)
	if err == nil {
		t.Fatal("parseConfig(-log-format yaml) succeeded, want an error")
	}
	if errors.Is(err, errUsage) {
		t.Errorf("parseConfig(-log-format yaml) error = %v, want a plain error main will print", err)
	}
}

// serve must stop when its context is cancelled, and must let a request that
// is already running finish first.
func TestServeDrainsInFlightRequestsOnShutdown(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}

	var (
		started = make(chan struct{})
		release = make(chan struct{})
	)
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(started)
		<-release
		w.WriteHeader(http.StatusOK)
		io.WriteString(w, "done")
	})

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	serveDone := make(chan error, 1)
	go func() { serveDone <- serve(ctx, ln, handler, slog.New(slog.DiscardHandler)) }()

	url := "http://" + ln.Addr().String() + "/slow"
	requestDone := make(chan *http.Response, 1)
	go func() {
		resp, err := http.Get(url)
		if err != nil {
			t.Errorf("GET %s: %v", url, err)
			requestDone <- nil
			return
		}
		requestDone <- resp
	}()

	select {
	case <-started:
	case <-time.After(5 * time.Second):
		t.Fatal("handler never started; serve did not accept the request")
	}

	// Shutdown begins while the handler is still running.
	cancel()
	close(release)

	select {
	case resp := <-requestDone:
		if resp == nil {
			t.Fatal("in-flight request failed during shutdown")
		}
		defer resp.Body.Close()
		body, _ := io.ReadAll(resp.Body)
		if resp.StatusCode != http.StatusOK || string(body) != "done" {
			t.Errorf("in-flight response = %d %q, want 200 \"done\"", resp.StatusCode, body)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("in-flight request was cut off by shutdown")
	}

	select {
	case err := <-serveDone:
		if err != nil {
			t.Fatalf("serve returned %v, want nil after a clean shutdown", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("serve did not return after its context was cancelled")
	}

	// The port must be released, not merely idle.
	if _, err := http.Get(url); err == nil {
		t.Error("the server still accepts requests after shutdown")
	}
}

func TestServeReportsListenerFailure(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	// A closed listener makes Accept fail immediately, which serve must
	// report rather than treat as a clean stop.
	ln.Close()

	err = serve(context.Background(), ln, http.NotFoundHandler(), slog.New(slog.DiscardHandler))
	if err == nil {
		t.Fatal("serve returned nil for a closed listener, want an error")
	}
}
