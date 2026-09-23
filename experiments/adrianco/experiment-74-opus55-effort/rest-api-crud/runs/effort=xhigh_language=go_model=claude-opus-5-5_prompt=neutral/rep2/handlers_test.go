package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

// newTestAPI starts an HTTP server backed by a fresh in-memory store.
func newTestAPI(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	store := newTestStore(t)
	srv := httptest.NewServer(NewServer(store, slog.New(slog.DiscardHandler)))
	t.Cleanup(srv.Close)
	return srv, store
}

type response struct {
	status int
	header http.Header
	body   []byte
}

func request(t *testing.T, srv *httptest.Server, method, path, body string) response {
	t.Helper()
	var rd io.Reader
	if body != "" {
		rd = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, srv.URL+path, rd)
	if err != nil {
		t.Fatalf("NewRequest: %v", err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatalf("read body: %v", err)
	}
	return response{status: resp.StatusCode, header: resp.Header, body: data}
}

func decode[T any](t *testing.T, r response) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(r.body, &v); err != nil {
		t.Fatalf("decode %s: %v", r.body, err)
	}
	return v
}

func expectStatus(t *testing.T, r response, want int) {
	t.Helper()
	if r.status != want {
		t.Fatalf("status = %d, want %d; body: %s", r.status, want, r.body)
	}
	if want != http.StatusNoContent {
		if ct := r.header.Get("Content-Type"); ct != "application/json" {
			t.Errorf("Content-Type = %q, want application/json", ct)
		}
	}
}

func TestHealth(t *testing.T) {
	srv, store := newTestAPI(t)

	r := request(t, srv, http.MethodGet, "/health", "")
	expectStatus(t, r, http.StatusOK)
	if got := decode[map[string]string](t, r); got["status"] != "ok" {
		t.Errorf("health = %v, want status ok", got)
	}

	// Once the database is gone, the health check must report it.
	store.Close()
	r = request(t, srv, http.MethodGet, "/health", "")
	expectStatus(t, r, http.StatusServiceUnavailable)
	if got := decode[map[string]string](t, r); got["status"] != "unavailable" {
		t.Errorf("health = %v, want status unavailable", got)
	}
}

func TestBookLifecycle(t *testing.T) {
	srv, _ := newTestAPI(t)

	// Create.
	r := request(t, srv, http.MethodPost, "/books",
		`{"title":"Nineteen Eighty-Four","author":"George Orwell","year":1949,"isbn":"978-0-452-28423-4"}`)
	expectStatus(t, r, http.StatusCreated)
	created := decode[Book](t, r)
	if created.ID == 0 || created.Title != "Nineteen Eighty-Four" || created.Author != "George Orwell" ||
		created.Year == nil || *created.Year != 1949 || created.ISBN == nil || *created.ISBN != "978-0-452-28423-4" {
		t.Fatalf("created = %+v, want all fields echoed with an ID", created)
	}
	bookPath := fmt.Sprintf("/books/%d", created.ID)
	if loc := r.header.Get("Location"); loc != bookPath {
		t.Errorf("Location = %q, want %q", loc, bookPath)
	}

	// Read back.
	r = request(t, srv, http.MethodGet, bookPath, "")
	expectStatus(t, r, http.StatusOK)
	if got := decode[Book](t, r); got.Title != created.Title || got.ID != created.ID {
		t.Errorf("GET = %+v, want %+v", got, created)
	}

	// List includes it.
	r = request(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, r, http.StatusOK)
	if list := decode[[]Book](t, r); len(list) != 1 || list[0].ID != created.ID {
		t.Errorf("list = %+v, want just the created book", list)
	}

	// Update replaces the whole resource; omitted optional fields become null.
	r = request(t, srv, http.MethodPut, bookPath, `{"title":"Animal Farm","author":"George Orwell"}`)
	expectStatus(t, r, http.StatusOK)
	updated := decode[Book](t, r)
	if updated.ID != created.ID || updated.Title != "Animal Farm" || updated.Year != nil || updated.ISBN != nil {
		t.Errorf("updated = %+v, want replaced title and null year/isbn", updated)
	}
	r = request(t, srv, http.MethodGet, bookPath, "")
	expectStatus(t, r, http.StatusOK)
	if got := decode[Book](t, r); got.Title != "Animal Farm" {
		t.Errorf("GET after PUT title = %q, want Animal Farm", got.Title)
	}

	// Delete, then it is gone.
	r = request(t, srv, http.MethodDelete, bookPath, "")
	expectStatus(t, r, http.StatusNoContent)
	if len(r.body) != 0 {
		t.Errorf("DELETE body = %q, want empty", r.body)
	}
	expectStatus(t, request(t, srv, http.MethodGet, bookPath, ""), http.StatusNotFound)
	expectStatus(t, request(t, srv, http.MethodDelete, bookPath, ""), http.StatusNotFound)
}

func TestNullableFieldsSerializeAsNull(t *testing.T) {
	srv, _ := newTestAPI(t)

	r := request(t, srv, http.MethodPost, "/books", `{"title":"Beowulf","author":"Unknown"}`)
	expectStatus(t, r, http.StatusCreated)
	raw := decode[map[string]any](t, r)
	for _, key := range []string{"year", "isbn"} {
		v, ok := raw[key]
		if !ok || v != nil {
			t.Errorf("%s = %v (present=%v), want explicit null", key, v, ok)
		}
	}
}

func TestListEmptyReturnsArray(t *testing.T) {
	srv, _ := newTestAPI(t)

	r := request(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, r, http.StatusOK)
	if got := strings.TrimSpace(string(r.body)); got != "[]" {
		t.Errorf("body = %s, want []", got)
	}
}

func TestListFilterByAuthor(t *testing.T) {
	srv, _ := newTestAPI(t)

	for _, body := range []string{
		`{"title":"Emma","author":"Jane Austen"}`,
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"Persuasion","author":"Jane Austen"}`,
	} {
		expectStatus(t, request(t, srv, http.MethodPost, "/books", body), http.StatusCreated)
	}

	tests := []struct {
		query string
		want  []string
	}{
		{"", []string{"Emma", "Dune", "Persuasion"}},
		{"?author=Jane+Austen", []string{"Emma", "Persuasion"}},
		{"?author=jane%20austen", []string{"Emma", "Persuasion"}},
		{"?author=Herbert", []string{"Dune"}},
		{"?author=Tolkien", []string{}},
		{"?author=", []string{"Emma", "Dune", "Persuasion"}},
	}
	for _, tc := range tests {
		t.Run(tc.query, func(t *testing.T) {
			r := request(t, srv, http.MethodGet, "/books"+tc.query, "")
			expectStatus(t, r, http.StatusOK)
			books := decode[[]Book](t, r)
			titles := []string{}
			for _, b := range books {
				titles = append(titles, b.Title)
			}
			if strings.Join(titles, ",") != strings.Join(tc.want, ",") {
				t.Errorf("titles = %v, want %v", titles, tc.want)
			}
		})
	}
}

func TestCreateValidation(t *testing.T) {
	srv, _ := newTestAPI(t)

	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string // keys expected in the "fields" object
	}{
		{"missing title", `{"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title":"T"}`, http.StatusBadRequest, []string{"author"}},
		{"blank title and author", `{"title":"  ","author":""}`, http.StatusBadRequest, []string{"title", "author"}},
		{"null title", `{"title":null,"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"year out of range", `{"title":"T","author":"A","year":99999}`, http.StatusBadRequest, []string{"year"}},
		{"year wrong type", `{"title":"T","author":"A","year":"1999"}`, http.StatusBadRequest, []string{"year"}},
		{"year not an integer", `{"title":"T","author":"A","year":1999.5}`, http.StatusBadRequest, []string{"year"}},
		{"title wrong type", `{"title":42,"author":"A"}`, http.StatusBadRequest, []string{"title"}},
		{"bad isbn", `{"title":"T","author":"A","isbn":"abc"}`, http.StatusBadRequest, []string{"isbn"}},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"malformed JSON", `{"title":`, http.StatusBadRequest, nil},
		{"syntax error", `{"title" "T"}`, http.StatusBadRequest, nil},
		{"array instead of object", `[{"title":"T","author":"A"}]`, http.StatusBadRequest, nil},
		{"trailing data", `{"title":"T","author":"A"} {}`, http.StatusBadRequest, nil},
		{"oversized body", `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`, http.StatusRequestEntityTooLarge, nil},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			r := request(t, srv, http.MethodPost, "/books", tc.body)
			expectStatus(t, r, tc.wantStatus)
			resp := decode[errorResponse](t, r)
			if resp.Error == "" {
				t.Errorf("error message missing in %s", r.body)
			}
			for _, f := range tc.wantFields {
				if resp.Fields[f] == "" {
					t.Errorf("fields[%q] missing in %s", f, r.body)
				}
			}
			if len(resp.Fields) != len(tc.wantFields) {
				t.Errorf("fields = %v, want exactly %v", resp.Fields, tc.wantFields)
			}
		})
	}

	// Nothing invalid may have been stored.
	r := request(t, srv, http.MethodGet, "/books", "")
	if list := decode[[]Book](t, r); len(list) != 0 {
		t.Errorf("stored %d books from invalid requests: %+v", len(list), list)
	}
}

func TestUpdateErrors(t *testing.T) {
	srv, _ := newTestAPI(t)

	r := request(t, srv, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	expectStatus(t, r, http.StatusCreated)
	bookPath := fmt.Sprintf("/books/%d", decode[Book](t, r).ID)

	// Validation applies to PUT too, and a rejected update leaves the book intact.
	r = request(t, srv, http.MethodPut, bookPath, `{"title":"New title"}`)
	expectStatus(t, r, http.StatusBadRequest)
	if resp := decode[errorResponse](t, r); resp.Fields["author"] == "" {
		t.Errorf("expected author field error, got %s", r.body)
	}
	r = request(t, srv, http.MethodGet, bookPath, "")
	if got := decode[Book](t, r); got.Title != "Dune" || got.Year == nil || *got.Year != 1965 {
		t.Errorf("book after rejected PUT = %+v, want unchanged", got)
	}

	expectStatus(t, request(t, srv, http.MethodPut, bookPath, `not json`), http.StatusBadRequest)
	expectStatus(t, request(t, srv, http.MethodPut, "/books/9999", `{"title":"T","author":"A"}`), http.StatusNotFound)
}

func TestInvalidAndUnknownIDs(t *testing.T) {
	srv, _ := newTestAPI(t)

	for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
		for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
			t.Run(method+" "+id, func(t *testing.T) {
				r := request(t, srv, method, "/books/"+id, `{"title":"T","author":"A"}`)
				expectStatus(t, r, http.StatusBadRequest)
			})
		}
		t.Run(method+" missing", func(t *testing.T) {
			r := request(t, srv, method, "/books/12345", `{"title":"T","author":"A"}`)
			expectStatus(t, r, http.StatusNotFound)
			if resp := decode[errorResponse](t, r); resp.Error != "book not found" {
				t.Errorf("error = %q, want %q", resp.Error, "book not found")
			}
		})
	}
}

func TestMethodNotAllowed(t *testing.T) {
	srv, _ := newTestAPI(t)

	r := request(t, srv, http.MethodPatch, "/books/1", `{}`)
	if r.status != http.StatusMethodNotAllowed {
		t.Errorf("PATCH status = %d, want 405", r.status)
	}
	r = request(t, srv, http.MethodDelete, "/books", "")
	if r.status != http.StatusMethodNotAllowed {
		t.Errorf("DELETE /books status = %d, want 405", r.status)
	}
}

func TestDatabaseFailureReturns500(t *testing.T) {
	srv, store := newTestAPI(t)
	store.Close()

	r := request(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, r, http.StatusInternalServerError)
	// Internal details must not leak to clients.
	if resp := decode[errorResponse](t, r); resp.Error != "internal server error" {
		t.Errorf("error = %q, want generic message", resp.Error)
	}
	expectStatus(t, request(t, srv, http.MethodPost, "/books", `{"title":"T","author":"A"}`), http.StatusInternalServerError)
}

func TestConcurrentCreatesOnFileDatabase(t *testing.T) {
	store, err := OpenStore(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	srv := httptest.NewServer(NewServer(store, slog.New(slog.DiscardHandler)))
	t.Cleanup(srv.Close)

	const n = 25
	var wg sync.WaitGroup
	statuses := make([]int, n)
	for i := range n {
		wg.Go(func() {
			body := fmt.Sprintf(`{"title":"Book %d","author":"Author %d"}`, i, i%3)
			resp, err := srv.Client().Post(srv.URL+"/books", "application/json", strings.NewReader(body))
			if err != nil {
				t.Errorf("POST: %v", err)
				return
			}
			resp.Body.Close()
			statuses[i] = resp.StatusCode
		})
	}
	wg.Wait()

	for i, s := range statuses {
		if s != http.StatusCreated {
			t.Errorf("request %d status = %d, want 201", i, s)
		}
	}
	r := request(t, srv, http.MethodGet, "/books", "")
	books := decode[[]Book](t, r)
	ids := make(map[int64]bool)
	for _, b := range books {
		ids[b.ID] = true
	}
	if len(books) != n || len(ids) != n {
		t.Errorf("got %d books with %d distinct IDs, want %d", len(books), len(ids), n)
	}
}
