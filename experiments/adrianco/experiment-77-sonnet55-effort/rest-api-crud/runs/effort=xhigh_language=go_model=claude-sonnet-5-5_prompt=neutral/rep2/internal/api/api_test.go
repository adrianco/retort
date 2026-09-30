package api

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"bookapi/internal/store"
)

func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	st, err := store.Open(":memory:")
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return serve(t, st)
}

func serve(t *testing.T, bs BookStore) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(New(bs, nil))
	t.Cleanup(srv.Close)
	return srv
}

// do sends a request and returns the status and raw body.
func do(t *testing.T, method, url, body string) (int, http.Header, string) {
	t.Helper()
	var rdr io.Reader
	if body != "" {
		rdr = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, rdr)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return resp.StatusCode, resp.Header, string(raw)
}

func decode[T any](t *testing.T, raw string) T {
	t.Helper()
	var v T
	if err := json.Unmarshal([]byte(raw), &v); err != nil {
		t.Fatalf("decode %q: %v", raw, err)
	}
	return v
}

func createBook(t *testing.T, srv *httptest.Server, body string) store.Book {
	t.Helper()
	status, _, raw := do(t, http.MethodPost, srv.URL+"/books", body)
	if status != http.StatusCreated {
		t.Fatalf("POST /books %s: status %d, body %s", body, status, raw)
	}
	return decode[store.Book](t, raw)
}

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	status, hdr, raw := do(t, http.MethodGet, srv.URL+"/health", "")
	if status != http.StatusOK {
		t.Fatalf("status = %d, want 200", status)
	}
	if ct := hdr.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
	if got := decode[map[string]string](t, raw); got["status"] != "ok" {
		t.Errorf("body = %s", raw)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	srv := newTestServer(t)

	status, hdr, raw := do(t, http.MethodPost, srv.URL+"/books",
		`{"title":"1984","author":"George Orwell","year":1949,"isbn":"978-0451524935"}`)
	if status != http.StatusCreated {
		t.Fatalf("POST status = %d, body %s", status, raw)
	}
	created := decode[store.Book](t, raw)
	if created.ID == 0 || created.Title != "1984" || created.Author != "George Orwell" ||
		created.Year == nil || *created.Year != 1949 || created.ISBN != "978-0451524935" {
		t.Errorf("created = %+v", created)
	}
	if loc := hdr.Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	status, _, raw = do(t, http.MethodGet, srv.URL+"/books/1", "")
	if status != http.StatusOK {
		t.Fatalf("GET status = %d, body %s", status, raw)
	}
	if got := decode[store.Book](t, raw); got.ID != created.ID || got.Title != "1984" {
		t.Errorf("GET returned %+v", got)
	}
}

func TestCreateTrimsAndAllowsMissingOptionalFields(t *testing.T) {
	srv := newTestServer(t)

	book := createBook(t, srv, `{"title":"  Dune  ","author":" Frank Herbert "}`)
	if book.Title != "Dune" || book.Author != "Frank Herbert" || book.Year != nil || book.ISBN != "" {
		t.Errorf("book = %+v", book)
	}

	_, _, raw := do(t, http.MethodGet, srv.URL+"/books/1", "")
	if !strings.Contains(raw, `"year":null`) {
		t.Errorf("expected null year in %s", raw)
	}
}

func TestCreateIgnoresClientSuppliedID(t *testing.T) {
	srv := newTestServer(t)
	book := createBook(t, srv, `{"id":99,"title":"T","author":"A"}`)
	if book.ID != 1 {
		t.Errorf("ID = %d, want server-assigned 1", book.ID)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	srv := newTestServer(t)

	status, _, raw := do(t, http.MethodGet, srv.URL+"/books", "")
	if status != http.StatusOK || strings.TrimSpace(raw) != "[]" {
		t.Fatalf("empty list: status %d, body %q; want 200 []", status, raw)
	}

	createBook(t, srv, `{"title":"1984","author":"George Orwell"}`)
	createBook(t, srv, `{"title":"Emma","author":"Jane Austen"}`)
	createBook(t, srv, `{"title":"Animal Farm","author":"George Orwell"}`)

	_, _, raw = do(t, http.MethodGet, srv.URL+"/books", "")
	if all := decode[[]store.Book](t, raw); len(all) != 3 {
		t.Errorf("unfiltered list has %d books, want 3", len(all))
	}

	_, _, raw = do(t, http.MethodGet, srv.URL+"/books?author=george+orwell", "")
	filtered := decode[[]store.Book](t, raw)
	if len(filtered) != 2 || filtered[0].Title != "1984" || filtered[1].Title != "Animal Farm" {
		t.Errorf("filtered list = %+v", filtered)
	}

	status, _, raw = do(t, http.MethodGet, srv.URL+"/books?author=Nobody", "")
	if status != http.StatusOK || strings.TrimSpace(raw) != "[]" {
		t.Errorf("no-match filter: status %d, body %q; want 200 []", status, raw)
	}
}

func TestUpdateBook(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"Old","author":"A","year":1990,"isbn":"1"}`)

	status, _, raw := do(t, http.MethodPut, srv.URL+"/books/1",
		`{"title":"New","author":"B","year":2001,"isbn":"2"}`)
	if status != http.StatusOK {
		t.Fatalf("PUT status = %d, body %s", status, raw)
	}
	updated := decode[store.Book](t, raw)
	if updated.ID != 1 || updated.Title != "New" || updated.Author != "B" ||
		updated.Year == nil || *updated.Year != 2001 || updated.ISBN != "2" {
		t.Errorf("updated = %+v", updated)
	}

	_, _, raw = do(t, http.MethodGet, srv.URL+"/books/1", "")
	if got := decode[store.Book](t, raw); got.Title != "New" {
		t.Errorf("GET after PUT = %+v", got)
	}
}

func TestUpdateMissingBookIs404(t *testing.T) {
	srv := newTestServer(t)
	status, _, raw := do(t, http.MethodPut, srv.URL+"/books/7", `{"title":"T","author":"A"}`)
	if status != http.StatusNotFound {
		t.Errorf("status = %d, want 404 (body %s)", status, raw)
	}
}

func TestUpdateValidatesBody(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"T","author":"A"}`)

	status, _, raw := do(t, http.MethodPut, srv.URL+"/books/1", `{"title":"","author":"A"}`)
	if status != http.StatusBadRequest {
		t.Errorf("status = %d, want 400 (body %s)", status, raw)
	}
	_, _, raw = do(t, http.MethodGet, srv.URL+"/books/1", "")
	if got := decode[store.Book](t, raw); got.Title != "T" {
		t.Errorf("rejected update modified the book: %+v", got)
	}
}

func TestDeleteBook(t *testing.T) {
	srv := newTestServer(t)
	createBook(t, srv, `{"title":"T","author":"A"}`)

	status, _, raw := do(t, http.MethodDelete, srv.URL+"/books/1", "")
	if status != http.StatusNoContent || raw != "" {
		t.Fatalf("DELETE: status %d, body %q; want 204 with empty body", status, raw)
	}
	if status, _, _ = do(t, http.MethodGet, srv.URL+"/books/1", ""); status != http.StatusNotFound {
		t.Errorf("GET after DELETE: status = %d, want 404", status)
	}
	if status, _, _ = do(t, http.MethodDelete, srv.URL+"/books/1", ""); status != http.StatusNotFound {
		t.Errorf("second DELETE: status = %d, want 404", status)
	}
}

func TestGetMissingBookIs404WithJSONError(t *testing.T) {
	srv := newTestServer(t)
	status, hdr, raw := do(t, http.MethodGet, srv.URL+"/books/123", "")
	if status != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", status)
	}
	if ct := hdr.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
	if e := decode[errorBody](t, raw); e.Error == "" {
		t.Errorf("body = %s, want an error message", raw)
	}
}

func TestInvalidBookID(t *testing.T) {
	srv := newTestServer(t)
	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			body := ""
			if method == http.MethodPut {
				body = `{"title":"T","author":"A"}`
			}
			if status, _, raw := do(t, method, srv.URL+"/books/"+id, body); status != http.StatusBadRequest {
				t.Errorf("%s /books/%s: status = %d, want 400 (body %s)", method, id, status, raw)
			}
		}
	}
}

func TestCreateValidation(t *testing.T) {
	srv := newTestServer(t)
	long := strings.Repeat("x", 256)

	tests := []struct {
		name      string
		body      string
		wantField string // field expected in details; empty when the whole body is at fault
	}{
		{"missing title", `{"author":"A"}`, "title"},
		{"blank title", `{"title":"   ","author":"A"}`, "title"},
		{"null title", `{"title":null,"author":"A"}`, "title"},
		{"missing author", `{"title":"T"}`, "author"},
		{"blank author", `{"title":"T","author":""}`, "author"},
		{"empty object", `{}`, "title"},
		{"title too long", `{"title":"` + long + `","author":"A"}`, "title"},
		{"author too long", `{"title":"T","author":"` + long + `"}`, "author"},
		{"isbn too long", `{"title":"T","author":"A","isbn":"` + strings.Repeat("9", 33) + `"}`, "isbn"},
		{"year zero", `{"title":"T","author":"A","year":0}`, "year"},
		{"negative year", `{"title":"T","author":"A","year":-5}`, "year"},
		{"year too large", `{"title":"T","author":"A","year":10000}`, "year"},
		{"year wrong type", `{"title":"T","author":"A","year":"1949"}`, "year"},
		{"fractional year", `{"title":"T","author":"A","year":1949.5}`, "year"},
		{"title wrong type", `{"title":42,"author":"A"}`, "title"},
		{"malformed json", `{"title":`, ""},
		{"not json", `hello`, ""},
		{"array body", `[]`, ""},
		{"trailing data", `{"title":"T","author":"A"} {}`, ""},
		{"empty body", ``, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			status, _, raw := do(t, http.MethodPost, srv.URL+"/books", tt.body)
			if status != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400 (body %s)", status, raw)
			}
			e := decode[errorBody](t, raw)
			if e.Error == "" {
				t.Errorf("no error message in %s", raw)
			}
			if tt.wantField != "" {
				if _, ok := e.Details[tt.wantField]; !ok {
					t.Errorf("details %v lack field %q", e.Details, tt.wantField)
				}
			}
		})
	}

	// Nothing invalid may have been persisted.
	_, _, raw := do(t, http.MethodGet, srv.URL+"/books", "")
	if got := decode[[]store.Book](t, raw); len(got) != 0 {
		t.Errorf("invalid requests created %d books", len(got))
	}
}

func TestValidationReportsAllProblems(t *testing.T) {
	srv := newTestServer(t)
	_, _, raw := do(t, http.MethodPost, srv.URL+"/books", `{"year":0}`)
	e := decode[errorBody](t, raw)
	for _, field := range []string{"title", "author", "year"} {
		if _, ok := e.Details[field]; !ok {
			t.Errorf("details %v lack field %q", e.Details, field)
		}
	}
}

func TestRequestBodyTooLarge(t *testing.T) {
	srv := newTestServer(t)
	body := `{"title":"T","author":"A","isbn":"` + strings.Repeat("x", maxBodyBytes) + `"}`
	if status, _, _ := do(t, http.MethodPost, srv.URL+"/books", body); status != http.StatusRequestEntityTooLarge {
		t.Errorf("status = %d, want 413", status)
	}
}

func TestUnknownRouteAndMethod(t *testing.T) {
	srv := newTestServer(t)

	if status, _, raw := do(t, http.MethodGet, srv.URL+"/nope", ""); status != http.StatusNotFound {
		t.Errorf("GET /nope: status = %d, want 404", status)
	} else if e := decode[errorBody](t, raw); e.Error == "" {
		t.Errorf("404 body is not a JSON error: %s", raw)
	}

	tests := []struct{ method, path, allow string }{
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPatch, "/books/1", "DELETE, GET, HEAD, PUT"},
		{http.MethodPost, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		status, hdr, raw := do(t, tt.method, srv.URL+tt.path, "")
		if status != http.StatusMethodNotAllowed {
			t.Errorf("%s %s: status = %d, want 405", tt.method, tt.path, status)
		}
		if got := hdr.Get("Allow"); got != tt.allow {
			t.Errorf("%s %s: Allow = %q, want %q", tt.method, tt.path, got, tt.allow)
		}
		if e := decode[errorBody](t, raw); e.Error == "" {
			t.Errorf("%s %s: 405 body is not a JSON error: %s", tt.method, tt.path, raw)
		}
	}
}

func TestHeadIsServedLikeGet(t *testing.T) {
	srv := newTestServer(t)
	status, _, raw := do(t, http.MethodHead, srv.URL+"/health", "")
	if status != http.StatusOK || raw != "" {
		t.Errorf("HEAD /health: status %d, body %q; want 200 with no body", status, raw)
	}
}

// failingStore fails every operation to exercise the error paths.
type failingStore struct{ err error }

func (f failingStore) Create(context.Context, store.Input) (store.Book, error) {
	return store.Book{}, f.err
}
func (f failingStore) Get(context.Context, int64) (store.Book, error) { return store.Book{}, f.err }
func (f failingStore) List(context.Context, string) ([]store.Book, error) {
	return nil, f.err
}
func (f failingStore) Update(context.Context, int64, store.Input) (store.Book, error) {
	return store.Book{}, f.err
}
func (f failingStore) Delete(context.Context, int64) error { return f.err }
func (f failingStore) Ping(context.Context) error          { return f.err }

func TestStoreFailuresAreHiddenBehind500(t *testing.T) {
	const secret = "disk on fire: /var/secret/path"
	srv := serve(t, failingStore{err: errors.New(secret)})

	tests := []struct{ method, path, body string }{
		{http.MethodPost, "/books", `{"title":"T","author":"A"}`},
		{http.MethodGet, "/books", ""},
		{http.MethodGet, "/books/1", ""},
		{http.MethodPut, "/books/1", `{"title":"T","author":"A"}`},
		{http.MethodDelete, "/books/1", ""},
	}
	for _, tt := range tests {
		status, _, raw := do(t, tt.method, srv.URL+tt.path, tt.body)
		if status != http.StatusInternalServerError {
			t.Errorf("%s %s: status = %d, want 500", tt.method, tt.path, status)
		}
		if strings.Contains(raw, "secret") {
			t.Errorf("%s %s leaked internal error: %s", tt.method, tt.path, raw)
		}
	}
}

func TestHealthReportsUnavailableWhenStoreIsDown(t *testing.T) {
	srv := serve(t, failingStore{err: errors.New("db down")})
	status, _, raw := do(t, http.MethodGet, srv.URL+"/health", "")
	if status != http.StatusServiceUnavailable {
		t.Errorf("status = %d, want 503", status)
	}
	if got := decode[map[string]string](t, raw); got["status"] != "unavailable" {
		t.Errorf("body = %s", raw)
	}
}

type panickingStore struct{ failingStore }

func (panickingStore) List(context.Context, string) ([]store.Book, error) { panic("boom") }

func TestPanicIsRecoveredAs500(t *testing.T) {
	srv := serve(t, panickingStore{})
	status, _, raw := do(t, http.MethodGet, srv.URL+"/books", "")
	if status != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", status)
	}
	if e := decode[errorBody](t, raw); e.Error == "" {
		t.Errorf("body = %s, want JSON error", raw)
	}
	// The server keeps serving after the panic.
	if status, _, _ := do(t, http.MethodGet, srv.URL+"/health", ""); status != http.StatusOK {
		t.Errorf("GET /health after panic: status = %d, want 200", status)
	}
}
