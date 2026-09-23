package main

import (
	"context"
	"errors"
	"flag"
	"io"
	"log/slog"
	"net"
	"net/http"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestParseConfig(t *testing.T) {
	env := map[string]string{"PORT": "9090", "DB_PATH": "/data/books.db"}
	tests := []struct {
		name string
		args []string
		env  map[string]string
		want config
	}{
		{"defaults", nil, nil, config{addr: ":8080", dbPath: "books.db"}},
		{"environment", nil, env, config{addr: ":9090", dbPath: "/data/books.db"}},
		{"flags", []string{"-addr", "127.0.0.1:7000", "-db", ":memory:"}, nil, config{addr: "127.0.0.1:7000", dbPath: ":memory:"}},
		{"flags override environment", []string{"-addr", ":7000", "-db", "other.db"}, env, config{addr: ":7000", dbPath: "other.db"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := parseConfig(tt.args, func(key string) string { return tt.env[key] }, io.Discard)
			if err != nil || got != tt.want {
				t.Errorf("parseConfig = %+v, %v; want %+v, nil", got, err, tt.want)
			}
		})
	}
}

func TestParseConfigRejectsBadArguments(t *testing.T) {
	noEnv := func(string) string { return "" }
	for _, args := range [][]string{
		{"-port", "8080"},
		{"-db", ""},
		{"serve"},
	} {
		if _, err := parseConfig(args, noEnv, io.Discard); err == nil {
			t.Errorf("parseConfig(%q) succeeded, want an error", args)
		}
	}
	if _, err := parseConfig([]string{"-h"}, noEnv, io.Discard); !errors.Is(err, flag.ErrHelp) {
		t.Errorf("parseConfig(-h) = %v, want flag.ErrHelp", err)
	}
}

// TestRun starts the real server on a free port, uses it, and checks that it
// shuts down cleanly when its context is cancelled.
func TestRun(t *testing.T) {
	addr := freeAddr(t)
	dbPath := filepath.Join(t.TempDir(), "books.db")
	ctx, cancel := context.WithCancel(t.Context())
	defer cancel()
	done := make(chan error, 1)
	go func() {
		done <- run(ctx, config{addr: addr, dbPath: dbPath}, slog.New(slog.DiscardHandler))
	}()

	client := &http.Client{Timeout: 5 * time.Second}
	defer client.CloseIdleConnections()
	base := "http://" + addr
	waitUntilHealthy(t, client, base+"/health", done)

	res, err := client.Post(base+"/books", "application/json",
		strings.NewReader(`{"title": "Dune", "author": "Frank Herbert", "year": 1965}`))
	if err != nil {
		t.Fatalf("POST /books: %v", err)
	}
	res.Body.Close()
	if res.StatusCode != http.StatusCreated {
		t.Fatalf("POST /books: status = %d, want %d", res.StatusCode, http.StatusCreated)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("run returned %v after shutdown, want nil", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("run did not return after its context was cancelled")
	}

	// The book was saved in the database file.
	books, err := openTestStore(t, dbPath).List(t.Context(), "")
	if err != nil || len(books) != 1 || books[0].Title != "Dune" {
		t.Errorf("database holds %s, %v; want just Dune", toJSON(books), err)
	}
}

func TestRunFailsWhenAddressIsTaken(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()

	cfg := config{addr: ln.Addr().String(), dbPath: filepath.Join(t.TempDir(), "books.db")}
	if err := run(t.Context(), cfg, slog.New(slog.DiscardHandler)); err == nil {
		t.Error("run succeeded on an address already in use, want an error")
	}
}

// freeAddr returns a local TCP address that nothing is listening on.
func freeAddr(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	ln.Close()
	return addr
}

// waitUntilHealthy polls url until it answers 200 OK. It fails the test if
// that takes too long, or if the server stops (reported on done) first.
func waitUntilHealthy(t *testing.T, client *http.Client, url string, done <-chan error) {
	t.Helper()
	deadline := time.Now().Add(10 * time.Second)
	for {
		select {
		case err := <-done:
			t.Fatalf("server stopped before becoming healthy: %v", err)
		default:
		}
		if res, err := client.Get(url); err == nil {
			res.Body.Close()
			if res.StatusCode == http.StatusOK {
				return
			}
		}
		if time.Now().After(deadline) {
			t.Fatalf("server at %s did not become healthy in time", url)
		}
		time.Sleep(20 * time.Millisecond)
	}
}
