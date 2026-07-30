// Command bookapi serves a small REST API for managing a book collection,
// backed by an embedded SQLite database.
package main

import (
	"context"
	"errors"
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	addr := flag.String("addr", envOr("BOOKAPI_ADDR", ":8080"), "TCP address to listen on")
	dbPath := flag.String("db", envOr("BOOKAPI_DB", "books.db"), `SQLite database file (":memory:" for an ephemeral database)`)
	flag.Parse()

	logger := log.New(os.Stderr, "bookapi ", log.LstdFlags|log.Lmsgprefix)

	if err := run(*addr, *dbPath, logger); err != nil {
		logger.Fatalf("fatal: %v", err)
	}
}

func run(addr, dbPath string, logger *log.Logger) error {
	store, err := OpenStore(dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	srv := &http.Server{
		Addr:              addr,
		Handler:           NewServer(store, logger),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	// Listen before announcing, so a port conflict is reported as an error
	// rather than a server that never accepts connections.
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	logger.Printf("listening on %s (database %s)", ln.Addr(), dbPath)

	errc := make(chan error, 1)
	go func() {
		if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errc <- err
			return
		}
		errc <- nil
	}()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	select {
	case err := <-errc:
		return err
	case <-ctx.Done():
		logger.Print("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			return err
		}
		return <-errc
	}
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
