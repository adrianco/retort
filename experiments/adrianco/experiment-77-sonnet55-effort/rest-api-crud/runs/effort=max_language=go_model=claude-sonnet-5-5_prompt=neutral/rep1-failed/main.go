// Command bookapi serves a small REST API for managing a book collection,
// backed by SQLite.
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
	defaultAddr   = ":8080"
	defaultDBPath = "books.db"

	// A request may wait api.RequestTimeout for its turn at the database and a
	// write can then wait up to store.BusyTimeout for a lock held by another
	// process. Allow a little longer than both to write the response, and for
	// in-flight requests to finish during shutdown.
	writeTimeout    = api.RequestTimeout + store.BusyTimeout + 2*time.Second
	shutdownTimeout = api.RequestTimeout + store.BusyTimeout + 2*time.Second
)

func main() {
	cfg, err := loadConfig(os.Args[1:], os.Getenv, os.Stderr)
	switch {
	case errors.Is(err, flag.ErrHelp):
		return
	case err != nil:
		os.Exit(2) // loadConfig has already explained the problem
	}

	logger := slog.New(slog.NewTextHandler(os.Stderr, nil))
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	// After the first signal, restore default handling so that a second
	// Ctrl-C terminates the process even if shutdown is stuck.
	context.AfterFunc(ctx, stop)

	a, err := newApp(cfg, logger)
	if err == nil {
		err = a.run(ctx)
	}
	if err != nil {
		logger.Error("bookapi failed", "err", err)
		os.Exit(1)
	}
}

// config holds the settings of a server run.
type config struct {
	addr   string
	dbPath string
}

// loadConfig reads settings from command-line flags. Their defaults come from
// the environment (ADDR or PORT, DB_PATH), so precedence is flag, environment,
// built-in default. Problems are reported on output.
func loadConfig(args []string, getenv func(string) string, output io.Writer) (config, error) {
	addr := defaultAddr
	if v := getenv("ADDR"); v != "" {
		addr = v
	} else if v := getenv("PORT"); v != "" {
		addr = ":" + v
	}
	dbPath := defaultDBPath
	if v := getenv("DB_PATH"); v != "" {
		dbPath = v
	}

	var cfg config
	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.SetOutput(output)
	fs.StringVar(&cfg.addr, "addr", addr, "address to listen on (env ADDR, or PORT for the port alone)")
	fs.StringVar(&cfg.dbPath, "db", dbPath,
		fmt.Sprintf("path of the SQLite database file, or %q for a throwaway database (env DB_PATH)", store.Memory))
	if err := fs.Parse(args); err != nil {
		return config{}, err
	}
	fail := func(msg string) (config, error) {
		fmt.Fprintln(output, msg)
		fs.Usage()
		return config{}, errors.New(msg)
	}
	switch {
	case fs.NArg() > 0:
		return fail(fmt.Sprintf("unexpected argument %q", fs.Arg(0)))
	case cfg.addr == "":
		// net.Listen would quietly pick a random port.
		return fail("-addr must not be empty")
	case cfg.dbPath == "":
		// SQLite would quietly use a temporary database that vanishes on exit.
		return fail("-db must not be empty")
	}
	return cfg, nil
}

// app is the assembled service: an open database and a bound listener.
type app struct {
	logger *slog.Logger
	store  *store.Store
	ln     net.Listener
	srv    *http.Server
}

// newApp opens the database and binds the listen address, so configuration
// problems surface before anything is served.
func newApp(cfg config, logger *slog.Logger) (*app, error) {
	st, err := store.Open(cfg.dbPath)
	if err != nil {
		return nil, err
	}
	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		st.Close()
		return nil, err
	}
	srv := &http.Server{
		Handler:           api.New(st, logger),
		ErrorLog:          slog.NewLogLogger(logger.Handler(), slog.LevelError),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      writeTimeout,
		IdleTimeout:       60 * time.Second,
	}
	return &app{logger: logger, store: st, ln: ln, srv: srv}, nil
}

// run serves requests until ctx is cancelled or the server fails. On
// cancellation it lets in-flight requests finish, then closes the database.
func (a *app) run(ctx context.Context) error {
	defer func() {
		if err := a.store.Close(); err != nil {
			a.logger.Error("closing database", "err", err)
		}
	}()

	serveErr := make(chan error, 1)
	go func() { serveErr <- a.srv.Serve(a.ln) }()
	a.logger.Info("listening", "addr", a.ln.Addr().String())

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
	}

	a.logger.Info("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := a.srv.Shutdown(shutdownCtx); err != nil {
		a.srv.Close()
		return fmt.Errorf("shutdown: %w", err)
	}
	return nil
}
