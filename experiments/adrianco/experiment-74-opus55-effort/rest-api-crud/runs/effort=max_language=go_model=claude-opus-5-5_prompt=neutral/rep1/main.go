// Command booksapi serves a REST API for managing a book collection stored in
// SQLite. See README.md for the endpoints and how to run it.
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
)

// shutdownTimeout is how long in-flight requests get to finish once the
// server has been told to stop.
const shutdownTimeout = 10 * time.Second

func main() {
	cfg, err := parseConfig(os.Args[1:], os.Getenv, os.Stderr)
	if errors.Is(err, flag.ErrHelp) {
		return
	}
	if err != nil {
		os.Exit(2) // parseConfig has already explained the problem
	}

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	err = run(ctx, cfg, logger)
	stop()
	if err != nil {
		logger.Error("server failed", "err", err)
		os.Exit(1)
	}
}

// config holds the service's settings.
type config struct {
	addr   string // TCP address to listen on, such as ":8080"
	dbPath string // SQLite database file, or ":memory:"
}

// parseConfig reads the settings from the command-line arguments, falling back
// to the PORT and DB_PATH environment variables and then to defaults. Any
// problem is reported to output as well as returned.
func parseConfig(args []string, getenv func(string) string, output io.Writer) (config, error) {
	cfg := config{addr: ":8080", dbPath: "books.db"}
	if port := getenv("PORT"); port != "" {
		cfg.addr = ":" + port
	}
	if path := getenv("DB_PATH"); path != "" {
		cfg.dbPath = path
	}

	fs := flag.NewFlagSet("booksapi", flag.ContinueOnError)
	fs.SetOutput(output)
	fs.StringVar(&cfg.addr, "addr", cfg.addr, "`address` to listen on (overrides $PORT)")
	fs.StringVar(&cfg.dbPath, "db", cfg.dbPath, "SQLite database `file`, or :memory: (overrides $DB_PATH)")
	if err := fs.Parse(args); err != nil {
		return config{}, err // fs has reported it
	}

	var err error
	switch {
	case fs.NArg() > 0:
		err = fmt.Errorf("unexpected argument %q", fs.Arg(0))
	case cfg.dbPath == "":
		err = errors.New("the database path must not be empty")
	}
	if err != nil {
		fmt.Fprintln(output, err)
		fs.Usage()
		return config{}, err
	}
	return cfg, nil
}

// run serves the API until ctx is cancelled, then shuts down gracefully.
func run(ctx context.Context, cfg config, logger *slog.Logger) error {
	store, err := OpenStore(ctx, cfg.dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		return err
	}
	srv := &http.Server{
		Handler:           NewServer(store, logger).Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      15 * time.Second,
		IdleTimeout:       time.Minute,
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelWarn),
	}

	serveErr := make(chan error, 1)
	go func() { serveErr <- srv.Serve(ln) }()
	logger.Info("listening", "addr", ln.Addr().String(), "db", cfg.dbPath)

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}

	logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	return srv.Shutdown(shutdownCtx)
}
