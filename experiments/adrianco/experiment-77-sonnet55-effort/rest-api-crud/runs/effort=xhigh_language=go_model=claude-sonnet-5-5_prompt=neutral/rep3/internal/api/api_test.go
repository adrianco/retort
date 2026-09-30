package api_test

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
	"bookapi/internal/store"
)

// newServer starts the API on a real in-memory SQLite store.
func newServer(t *testing.T) *httptest.Server {
	t.Helper()
	st, err := store.Open(":memory:")
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return serve(t, st)
}

func serve(t *testing.T, s api.BookStore) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(api.New(s, slog.New(slog.DiscardHandler)))
	t.Cleanup(srv.Close)
	return srv
}

// do sends a request and returns the response with its body fully read.
func do(t *testing.T, srv *httptest.Server, method, path, body string) (*http.Response, []byte) {
	t.Helper()
	req, err := http.NewRequest(method, srv.URL+path, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	return resp, data
}

func decode[T any](t *testing.T, data []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(data, &v); err != nil {
		t.Fatalf("response is not the expected JSON (%v): %s", err, data)
	}
	return v
}

func wantStatus(t *testing.T, resp *http.Response, body []byte, want int) {
	t.Helper()
	if resp.StatusCode != want {
		t.Fatalf("status = %d, want %d; body: %s", resp.StatusCode, want, body)
	}
}

func mustCreate(t *testing.T, srv *httptest.Server, body string) book.Book {
	t.Helper()
	resp, data := do(t, srv, "POST", "/books", body)
	wantStatus(t, resp, data, http.StatusCreated)
	return decode[book.Book](t, data)
}

func TestHealth(t *testing.T) {
	srv := newServer(t)
	resp, data := do(t, srv, "GET", "/health", "")
	wantStatus(t, resp, data, http.StatusOK)
	if got := decode[map[string]string](t, data); got["status"] != "ok" {
		t.Errorf("body = %s, want status ok", data)
	}
	if ct := resp.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

func TestCreateBook(t *testing.T) {
	srv := newServer(t)
	resp, data := do(t, srv, "POST", "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0441172719"}`)
	wantStatus(t, resp, data, http.StatusCreated)

	got := decode[book.Book](t, data)
	want := book.Book{ID: got.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "978-0441172719"}
	if got != want || got.ID < 1 {
		t.Errorf("created = %+v, want %+v with a positive id", got, want)
	}
	if loc := resp.Header.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
	if ct := resp.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

func TestCreateThenGet(t *testing.T) {
	srv := newServer(t)
	created := mustCreate(t, srv, `{"title":"Neuromancer","author":"William Gibson","year":1984,"isbn":"0441569595"}`)

	resp, data := do(t, srv, "GET", "/books/"+itoa(created.ID), "")
	wantStatus(t, resp, data, http.StatusOK)
	if got := decode[book.Book](t, data); got != created {
		t.Errorf("GET = %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newServer(t)
	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"blank title", `{"title":"  ","author":"A"}`, []string{"title"}},
		{"missing author", `{"title":"T"}`, []string{"author"}},
		{"blank author", `{"title":"T","author":""}`, []string{"author"}},
		{"both missing", `{}`, []string{"title", "author"}},
		{"null body value", `null`, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-5}`, []string{"year"}},
		{"far future year", `{"title":"T","author":"A","year":100000}`, []string{"year"}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, data := do(t, srv, "POST", "/books", tc.body)
			wantStatus(t, resp, data, http.StatusBadRequest)
			got := decode[struct {
				Error   string            `json:"error"`
				Details map[string]string `json:"details"`
			}](t, data)
			if got.Error == "" {
				t.Error("error message is empty")
			}
			for _, f := range tc.fields {
				if got.Details[f] == "" {
					t.Errorf("details missing entry for %q: %s", f, data)
				}
			}
			if len(got.Details) != len(tc.fields) {
				t.Errorf("details = %v, want exactly fields %v", got.Details, tc.fields)
			}
		})
	}

	// None of the rejected requests may have stored anything.
	resp, data := do(t, srv, "GET", "/books", "")
	wantStatus(t, resp, data, http.StatusOK)
	if got := decode[[]book.Book](t, data); len(got) != 0 {
		t.Errorf("rejected requests stored %d books", len(got))
	}
}

func TestCreateMalformedBodies(t *testing.T) {
	srv := newServer(t)
	tests := []struct {
		name string
		body string
		want int
	}{
		{"empty body", ``, http.StatusBadRequest},
		{"not json", `title=Dune`, http.StatusBadRequest},
		{"truncated json", `{"title":"Dune"`, http.StatusBadRequest},
		{"array instead of object", `[]`, http.StatusBadRequest},
		{"year as string", `{"title":"T","author":"A","year":"1965"}`, http.StatusBadRequest},
		{"fractional year", `{"title":"T","author":"A","year":1965.5}`, http.StatusBadRequest},
		{"title as number", `{"title":42,"author":"A"}`, http.StatusBadRequest},
		{"trailing garbage", `{"title":"T","author":"A"} {"x":1}`, http.StatusBadRequest},
		{"oversized body", `{"title":"` + strings.Repeat("x", 2<<20) + `","author":"A"}`, http.StatusRequestEntityTooLarge},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			resp, data := do(t, srv, "POST", "/books", tc.body)
			wantStatus(t, resp, data, tc.want)
			if got := decode[map[string]any](t, data); got["error"] == nil || got["error"] == "" {
				t.Errorf("want an error message, got %s", data)
			}
		})
	}
}

func TestCreateIgnoresClientSuppliedID(t *testing.T) {
	srv := newServer(t)
	b := mustCreate(t, srv, `{"id":999,"title":"T","author":"A"}`)
	if b.ID == 999 {
		t.Error("server accepted a client-chosen id")
	}
}

func TestCreateTrimsWhitespace(t *testing.T) {
	srv := newServer(t)
	b := mustCreate(t, srv, `{"title":"  Dune  ","author":" Frank Herbert "}`)
	if b.Title != "Dune" || b.Author != "Frank Herbert" {
		t.Errorf("got %+v, want trimmed title and author", b)
	}
}

func TestListBooks(t *testing.T) {
	srv := newServer(t)

	resp, data := do(t, srv, "GET", "/books", "")
	wantStatus(t, resp, data, http.StatusOK)
	if strings.TrimSpace(string(data)) != "[]" {
		t.Errorf("empty list body = %q, want []", data)
	}

	mustCreate(t, srv, `{"title":"1984","author":"George Orwell","year":1949}`)
	mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	mustCreate(t, srv, `{"title":"Animal Farm","author":"George Orwell","year":1945}`)

	resp, data = do(t, srv, "GET", "/books", "")
	wantStatus(t, resp, data, http.StatusOK)
	all := decode[[]book.Book](t, data)
	if len(all) != 3 {
		t.Fatalf("got %d books, want 3: %s", len(all), data)
	}
	if all[0].Title != "1984" || all[1].Title != "Dune" || all[2].Title != "Animal Farm" {
		t.Errorf("unexpected order: %+v", all)
	}
}

func TestListFilterByAuthor(t *testing.T) {
	srv := newServer(t)
	mustCreate(t, srv, `{"title":"1984","author":"George Orwell"}`)
	mustCreate(t, srv, `{"title":"Dune","author":"Frank Herbert"}`)
	mustCreate(t, srv, `{"title":"Animal Farm","author":"George Orwell"}`)

	tests := []struct {
		query string
		want  []string
	}{
		{"?author=George+Orwell", []string{"1984", "Animal Farm"}},
		{"?author=george%20orwell", []string{"1984", "Animal Farm"}},
		{"?author=Frank+Herbert", []string{"Dune"}},
		{"?author=Nobody", nil},
		{"?author=", []string{"1984", "Dune", "Animal Farm"}}, // empty filter = no filter
	}
	for _, tc := range tests {
		t.Run(tc.query, func(t *testing.T) {
			resp, data := do(t, srv, "GET", "/books"+tc.query, "")
			wantStatus(t, resp, data, http.StatusOK)
			got := decode[[]book.Book](t, data)
			var titles []string
			for _, b := range got {
				titles = append(titles, b.Title)
			}
			if strings.Join(titles, "|") != strings.Join(tc.want, "|") {
				t.Errorf("titles = %v, want %v", titles, tc.want)
			}
			if got == nil {
				t.Error("list decoded as null, want []")
			}
		})
	}
}

func TestGetBookNotFound(t *testing.T) {
	srv := newServer(t)
	resp, data := do(t, srv, "GET", "/books/12345", "")
	wantStatus(t, resp, data, http.StatusNotFound)
	if got := decode[map[string]string](t, data); got["error"] == "" {
		t.Errorf("want error message, got %s", data)
	}
}

func TestInvalidIDs(t *testing.T) {
	srv := newServer(t)
	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		for _, method := range []string{"GET", "PUT", "DELETE"} {
			body := ""
			if method == "PUT" {
				body = `{"title":"T","author":"A"}`
			}
			resp, data := do(t, srv, method, "/books/"+id, body)
			if resp.StatusCode != http.StatusBadRequest {
				t.Errorf("%s /books/%s = %d, want 400; body: %s", method, id, resp.StatusCode, data)
			}
		}
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newServer(t)
	created := mustCreate(t, srv, `{"title":"Draft","author":"Anon","year":2000,"isbn":"111"}`)
	path := "/books/" + itoa(created.ID)

	resp, data := do(t, srv, "PUT", path, `{"title":"Final","author":"Known","year":2024,"isbn":"222"}`)
	wantStatus(t, resp, data, http.StatusOK)
	want := book.Book{ID: created.ID, Title: "Final", Author: "Known", Year: 2024, ISBN: "222"}
	if got := decode[book.Book](t, data); got != want {
		t.Errorf("PUT response = %+v, want %+v", got, want)
	}

	resp, data = do(t, srv, "GET", path, "")
	wantStatus(t, resp, data, http.StatusOK)
	if got := decode[book.Book](t, data); got != want {
		t.Errorf("GET after PUT = %+v, want %+v", got, want)
	}
}

func TestUpdateValidationAndNotFound(t *testing.T) {
	srv := newServer(t)
	created := mustCreate(t, srv, `{"title":"Keep","author":"Me"}`)
	path := "/books/" + itoa(created.ID)

	resp, data := do(t, srv, "PUT", path, `{"title":"","author":"Me"}`)
	wantStatus(t, resp, data, http.StatusBadRequest)
	resp, data = do(t, srv, "PUT", path, `not json`)
	wantStatus(t, resp, data, http.StatusBadRequest)

	// The failed updates must leave the book untouched.
	resp, data = do(t, srv, "GET", path, "")
	wantStatus(t, resp, data, http.StatusOK)
	if got := decode[book.Book](t, data); got != created {
		t.Errorf("book changed by rejected update: %+v", got)
	}

	resp, data = do(t, srv, "PUT", "/books/777", `{"title":"T","author":"A"}`)
	wantStatus(t, resp, data, http.StatusNotFound)
}

func TestDeleteBook(t *testing.T) {
	srv := newServer(t)
	keep := mustCreate(t, srv, `{"title":"Keep","author":"A"}`)
	gone := mustCreate(t, srv, `{"title":"Gone","author":"A"}`)

	resp, data := do(t, srv, "DELETE", "/books/"+itoa(gone.ID), "")
	wantStatus(t, resp, data, http.StatusNoContent)
	if len(data) != 0 {
		t.Errorf("204 response has a body: %q", data)
	}

	resp, data = do(t, srv, "GET", "/books/"+itoa(gone.ID), "")
	wantStatus(t, resp, data, http.StatusNotFound)
	resp, data = do(t, srv, "DELETE", "/books/"+itoa(gone.ID), "")
	wantStatus(t, resp, data, http.StatusNotFound)

	resp, data = do(t, srv, "GET", "/books/"+itoa(keep.ID), "")
	wantStatus(t, resp, data, http.StatusOK)
}

func TestRoutingErrors(t *testing.T) {
	srv := newServer(t)
	tests := []struct {
		method, path string
		want         int
		allow        string
	}{
		{"GET", "/nope", http.StatusNotFound, ""},
		{"GET", "/books/1/extra", http.StatusNotFound, ""},
		{"GET", "/", http.StatusNotFound, ""},
		{"PATCH", "/books", http.StatusMethodNotAllowed, "GET, POST"},
		{"DELETE", "/books", http.StatusMethodNotAllowed, "GET, POST"},
		{"POST", "/books/1", http.StatusMethodNotAllowed, "GET, PUT, DELETE"},
		{"POST", "/health", http.StatusMethodNotAllowed, "GET"},
	}
	for _, tc := range tests {
		t.Run(tc.method+" "+tc.path, func(t *testing.T) {
			resp, data := do(t, srv, tc.method, tc.path, "")
			wantStatus(t, resp, data, tc.want)
			if got := resp.Header.Get("Allow"); got != tc.allow {
				t.Errorf("Allow = %q, want %q", got, tc.allow)
			}
			if ct := resp.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
				t.Errorf("Content-Type = %q, want JSON error body", ct)
			}
		})
	}
}

// failingStore makes every operation fail, to exercise the 500/503 paths.
type failingStore struct{ err error }

func (f failingStore) Create(context.Context, book.Input) (book.Book, error) {
	return book.Book{}, f.err
}
func (f failingStore) List(context.Context, string) ([]book.Book, error) { return nil, f.err }
func (f failingStore) Get(context.Context, int64) (book.Book, error)     { return book.Book{}, f.err }
func (f failingStore) Update(context.Context, int64, book.Input) (book.Book, error) {
	return book.Book{}, f.err
}
func (f failingStore) Delete(context.Context, int64) error { return f.err }
func (f failingStore) Ping(context.Context) error          { return f.err }

func TestStoreFailuresReturn500WithoutLeakingDetails(t *testing.T) {
	const secret = "disk I/O error: /var/secret/path"
	srv := serve(t, failingStore{err: errors.New(secret)})

	tests := []struct{ method, path, body string }{
		{"POST", "/books", `{"title":"T","author":"A"}`},
		{"GET", "/books", ""},
		{"GET", "/books/1", ""},
		{"PUT", "/books/1", `{"title":"T","author":"A"}`},
		{"DELETE", "/books/1", ""},
	}
	for _, tc := range tests {
		resp, data := do(t, srv, tc.method, tc.path, tc.body)
		if resp.StatusCode != http.StatusInternalServerError {
			t.Errorf("%s %s = %d, want 500; body: %s", tc.method, tc.path, resp.StatusCode, data)
		}
		if bytes.Contains(data, []byte("secret")) {
			t.Errorf("%s %s leaked internal error: %s", tc.method, tc.path, data)
		}
	}
}

func TestHealthReportsUnavailableWhenDatabaseDown(t *testing.T) {
	srv := serve(t, failingStore{err: errors.New("db down")})
	resp, data := do(t, srv, "GET", "/health", "")
	wantStatus(t, resp, data, http.StatusServiceUnavailable)
	if got := decode[map[string]string](t, data); got["status"] != "unavailable" {
		t.Errorf("body = %s, want status unavailable", data)
	}
}

// panickingStore lets us check that a handler panic becomes a JSON 500 and
// the server keeps serving afterwards.
type panickingStore struct{ failingStore }

func (panickingStore) List(context.Context, string) ([]book.Book, error) { panic("boom") }

func TestPanicIsRecovered(t *testing.T) {
	srv := serve(t, panickingStore{})

	resp, data := do(t, srv, "GET", "/books", "")
	wantStatus(t, resp, data, http.StatusInternalServerError)
	if got := decode[map[string]string](t, data); got["error"] != "internal server error" {
		t.Errorf("body = %s", data)
	}
	// Server must still be alive.
	resp, data = do(t, srv, "GET", "/nope", "")
	wantStatus(t, resp, data, http.StatusNotFound)
}

func itoa(id int64) string {
	b, _ := json.Marshal(id)
	return string(b)
}
