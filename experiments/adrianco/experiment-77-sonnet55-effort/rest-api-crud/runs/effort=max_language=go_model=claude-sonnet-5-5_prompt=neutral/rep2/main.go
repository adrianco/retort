// Command bookapi serves a REST API for managing a book collection, stored in
// an embedded SQLite database.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"bookapi/internal/api"
	"bookapi/internal/store"
)

const (
	defaultAddr     = ":8080"
	defaultDBPath   = "books.db"
	shutdownTimeout = 10 * time.Second
)

type config struct {
	addr   string // listen address, e.g. ":8080" or "127.0.0.1:9000"
	dbPath string // SQLite database file
}

// loadConfig builds the configuration from command-line flags, which take
// precedence, then the PORT and DB_PATH environment variables, then defaults.
// Problems are reported to stderr before the error is returned.
func loadConfig(args []string, getenv func(string) string, stderr io.Writer) (config, error) {
	cfg := config{addr: defaultAddr, dbPath: defaultDBPath}
	if port := getenv("PORT"); port != "" {
		cfg.addr = ":" + port
	}
	if path := getenv("DB_PATH"); path != "" {
		cfg.dbPath = path
	}

	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.SetOutput(stderr)
	fs.StringVar(&cfg.addr, "addr", cfg.addr, "address to listen on (env PORT sets the port)")
	fs.StringVar(&cfg.dbPath, "db", cfg.dbPath, "path of the SQLite database file (env DB_PATH)")
	if err := fs.Parse(args); err != nil {
		return config{}, err
	}
	if fs.NArg() > 0 {
		err := fmt.Errorf("unexpected argument %q", fs.Arg(0))
		fmt.Fprintln(fs.Output(), err)
		fs.Usage()
		return config{}, err
	}
	return cfg, nil
}

// run opens the database and serves the API until ctx is cancelled, then shuts
// down gracefully: in-flight requests finish before the database is closed.
// ready, if not nil, is called with the bound address once the server accepts
// connections.
func run(ctx context.Context, cfg config, logger *slog.Logger, ready func(net.Addr)) error {
	st, err := store.Open(cfg.dbPath)
	if err != nil {
		return err
	}
	defer st.Close()

	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		return err
	}

	srv := &http.Server{
		Handler:           api.New(st, logger),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       60 * time.Second,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelError),
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	logger.Info("listening", "addr", ln.Addr().String(), "db", cfg.dbPath)
	if ready != nil {
		ready(ln.Addr())
	}

	select {
	case err := <-serveErr:
		return err // Serve only returns on failure until Shutdown is called
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	if err := <-serveErr; !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))

	cfg, err := loadConfig(os.Args[1:], os.Getenv, os.Stderr)
	switch {
	case errors.Is(err, flag.ErrHelp):
		return
	case err != nil:
		os.Exit(2) // loadConfig has already told the user what is wrong
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	err = run(ctx, cfg, logger, nil)
	stop()
	if err != nil {
		logger.Error("server failed", "error", err)
		os.Exit(1)
	}
}
