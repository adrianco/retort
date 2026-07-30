// Command bookapi serves a REST API for a book collection, backed by SQLite.
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

const shutdownTimeout = 10 * time.Second

// errUsage marks an error the flag package has already written to stderr,
// along with the usage text, so main does not report it a second time.
var errUsage = errors.New("invalid command line")

func main() {
	err := run()
	switch {
	case err == nil:
	case errors.Is(err, flag.ErrHelp):
		// -h or -help: the usage text is the requested output.
		os.Exit(0)
	case errors.Is(err, errUsage):
		os.Exit(2)
	default:
		// The logger may not exist yet, so report startup failures directly.
		fmt.Fprintf(os.Stderr, "bookapi: %v\n", err)
		os.Exit(1)
	}
}

type config struct {
	addr   string
	dbPath string
	logFmt string
}

// parseConfig resolves configuration from the environment and then the given
// command line, so an explicit flag always wins over an environment variable.
// Flag errors and the usage text are written to output.
func parseConfig(args []string, output io.Writer) (config, error) {
	addr := ":8080"
	// PORT is the convention most container hosts use to assign a port.
	if port := os.Getenv("PORT"); port != "" {
		addr = ":" + port
	}
	cfg := config{
		addr:   envOr("BOOKAPI_ADDR", addr),
		dbPath: envOr("BOOKAPI_DB", "books.db"),
		logFmt: envOr("BOOKAPI_LOG_FORMAT", "text"),
	}

	fs := flag.NewFlagSet("bookapi", flag.ContinueOnError)
	fs.SetOutput(output)
	fs.StringVar(&cfg.addr, "addr", cfg.addr, "TCP address to listen on")
	fs.StringVar(&cfg.dbPath, "db", cfg.dbPath, `SQLite database file (":memory:" for an ephemeral database)`)
	fs.StringVar(&cfg.logFmt, "log-format", cfg.logFmt, `log format: "text" or "json"`)
	if err := fs.Parse(args); err != nil {
		// Parse has already written the message and usage to output.
		return config{}, errors.Join(errUsage, err)
	}

	if cfg.logFmt != "text" && cfg.logFmt != "json" {
		return config{}, fmt.Errorf(`invalid -log-format %q: want "text" or "json"`, cfg.logFmt)
	}
	return cfg, nil
}

func run() error {
	cfg, err := parseConfig(os.Args[1:], os.Stderr)
	if err != nil {
		return err
	}

	log := newLogger(cfg.logFmt)

	// Interrupt handling starts before the listener so a signal during
	// startup still stops the process cleanly.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	store, err := OpenStore(ctx, cfg.dbPath)
	if err != nil {
		return err
	}
	defer store.Close()

	ln, err := net.Listen("tcp", cfg.addr)
	if err != nil {
		return fmt.Errorf("listen on %s: %w", cfg.addr, err)
	}

	log.Info("listening", "addr", ln.Addr().String(), "database", cfg.dbPath)

	return serve(ctx, ln, NewAPI(store, log).Routes(), log)
}

// serve handles requests on ln until ctx is cancelled, then stops accepting
// and gives in-flight requests up to shutdownTimeout to finish.
func serve(ctx context.Context, ln net.Listener, handler http.Handler, log *slog.Logger) error {
	srv := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
		ErrorLog:          slog.NewLogLogger(log.Handler(), slog.LevelError),
	}

	serveErr := make(chan error, 1)
	go func() {
		// Serve always returns non-nil; ErrServerClosed means Shutdown ran.
		if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
			serveErr <- err
			return
		}
		serveErr <- nil
	}()

	select {
	case err := <-serveErr:
		return err
	case <-ctx.Done():
		log.Info("shutting down", "timeout", shutdownTimeout.String())
	}

	// A fresh context: ctx is already cancelled.
	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown: %w", err)
	}
	// Surface any error Serve reported while shutting down.
	if err := <-serveErr; err != nil {
		return err
	}

	log.Info("stopped")
	return nil
}

func newLogger(format string) *slog.Logger {
	opts := &slog.HandlerOptions{Level: slog.LevelInfo}
	if format == "json" {
		return slog.New(slog.NewJSONHandler(os.Stderr, opts))
	}
	return slog.New(slog.NewTextHandler(os.Stderr, opts))
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
