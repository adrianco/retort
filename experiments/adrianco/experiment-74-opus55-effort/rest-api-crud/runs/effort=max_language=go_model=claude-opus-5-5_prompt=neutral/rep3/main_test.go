package main

import (
	"context"
	"io"
	"net"
	"net/http"
	"testing"
	"time"
)

// TestServeShutsDownGracefully cancels serve's context while a request is in
// flight: the request must still complete, and serve must then return nil.
func TestServeShutsDownGracefully(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	started, release := make(chan struct{}), make(chan struct{})
	slow := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		close(started)
		<-release
		io.WriteString(w, "finished")
	})

	ctx, cancel := context.WithCancel(t.Context())
	serveErr := make(chan error, 1)
	go func() { serveErr <- serve(ctx, ln, slow) }()

	type result struct {
		body string
		err  error
	}
	response := make(chan result, 1)
	go func() {
		resp, err := http.Get("http://" + ln.Addr().String() + "/")
		if err != nil {
			response <- result{err: err}
			return
		}
		defer resp.Body.Close()
		body, err := io.ReadAll(resp.Body)
		response <- result{string(body), err}
	}()

	select {
	case <-started:
	case <-time.After(5 * time.Second):
		t.Fatal("request never reached the handler")
	}
	cancel() // shut down while the request is still being handled

	select {
	case err := <-serveErr:
		t.Fatalf("serve returned %v before the in-flight request finished", err)
	case <-time.After(100 * time.Millisecond):
	}

	close(release)
	if r := <-response; r.err != nil || r.body != "finished" {
		t.Errorf("in-flight request got body %q, error %v; want it to complete", r.body, r.err)
	}
	select {
	case err := <-serveErr:
		if err != nil {
			t.Errorf("serve returned %v, want nil after a clean shutdown", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("serve did not return after shutdown")
	}
	if conn, err := net.Dial("tcp", ln.Addr().String()); err == nil {
		conn.Close()
		t.Error("server still accepts connections after shutdown")
	}
}

func TestServeReturnsListenerErrors(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	ln.Close()

	if err := serve(t.Context(), ln, http.NotFoundHandler()); err == nil {
		t.Error("serve on a closed listener returned nil, want an error")
	}
}
