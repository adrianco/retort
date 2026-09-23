package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func newTestServer(t *testing.T) (*Server, *Store) {
	t.Helper()
	st := newTestStore(t)
	return NewServer(st, slog.New(slog.DiscardHandler)), st
}

func do(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r io.Reader
	if body != "" {
		r = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, target, r)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func decodeBody[T any](t *testing.T, rec *httptest.ResponseRecorder) T {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json (body %q)", ct, rec.Body.String())
	}
	var v T
	if err := json.Unmarshal(rec.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
	return v
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d (body %q)", rec.Code, want, rec.Body.String())
	}
}

func createBook(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	expectStatus(t, rec, http.StatusCreated)
	return decodeBody[Book](t, rec)
}

func TestHealth(t *testing.T) {
	srv, st := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBody[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("status = %q, want ok", got["status"])
	}

	st.Close()
	rec = do(t, srv, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusServiceUnavailable)
	if got := decodeBody[map[string]string](t, rec); got["status"] != "unavailable" {
		t.Errorf("status = %q, want unavailable", got["status"])
	}
}

func TestCreateBook(t *testing.T) {
	srv, _ := newTestServer(t)

	rec := do(t, srv, http.MethodPost, "/books",
		`{"title":"  The Hobbit ","author":"J.R.R. Tolkien","year":1937,"isbn":"978-0-306-40615-7"}`)
	expectStatus(t, rec, http.StatusCreated)
	book := decodeBody[Book](t, rec)

	if book.ID < 1 {
		t.Errorf("id = %d, want positive", book.ID)
	}
	if loc := rec.Header().Get("Location"); loc != fmt.Sprintf("/books/%d", book.ID) {
		t.Errorf("Location = %q, want /books/%d", loc, book.ID)
	}
	if book.Title != "The Hobbit" || book.Author != "J.R.R. Tolkien" {
		t.Errorf("title/author = %q/%q", book.Title, book.Author)
	}
	if book.Year == nil || *book.Year != 1937 {
		t.Errorf("year = %v, want 1937", book.Year)
	}
	if book.ISBN == nil || *book.ISBN != "9780306406157" {
		t.Errorf("isbn = %v, want normalized 9780306406157", book.ISBN)
	}
	if book.CreatedAt.IsZero() || !book.CreatedAt.Equal(book.UpdatedAt) {
		t.Errorf("created_at = %v, updated_at = %v; want equal and non-zero", book.CreatedAt, book.UpdatedAt)
	}

	// The book is retrievable at its Location.
	rec = do(t, srv, http.MethodGet, rec.Header().Get("Location"), "")
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got.ID != book.ID || got.Title != book.Title || !got.CreatedAt.Equal(book.CreatedAt) {
		t.Errorf("GET returned %+v, want %+v", got, book)
	}
}

func TestCreateBookOptionalFieldsAreNull(t *testing.T) {
	srv, _ := newTestServer(t)

	rec := do(t, srv, http.MethodPost, "/books", `{"title":"Beowulf","author":"Unknown","isbn":""}`)
	expectStatus(t, rec, http.StatusCreated)
	raw := decodeBody[map[string]any](t, rec)
	for _, key := range []string{"year", "isbn"} {
		if v, ok := raw[key]; !ok || v != nil {
			t.Errorf("%s = %v (present %v), want null", key, v, ok)
		}
	}
}

func TestCreateBookValidation(t *testing.T) {
	srv, _ := newTestServer(t)

	tests := []struct {
		name   string
		body   string
		fields []string
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"missing author", `{"title":"T"}`, []string{"author"}},
		{"missing both", `{}`, []string{"title", "author"}},
		{"blank title and author", `{"title":"   ","author":""}`, []string{"title", "author"}},
		{"null object", `null`, []string{"title", "author"}},
		{"year out of range", `{"title":"T","author":"A","year":3000}`, []string{"year"}},
		{"invalid isbn", `{"title":"T","author":"A","isbn":"978-0-306-40615-8"}`, []string{"isbn"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tt.body)
			expectStatus(t, rec, http.StatusBadRequest)
			resp := decodeBody[errorResponse](t, rec)
			if resp.Error != "validation failed" {
				t.Errorf("error = %q, want %q", resp.Error, "validation failed")
			}
			if len(resp.Fields) != len(tt.fields) {
				t.Errorf("fields = %v, want exactly %v", resp.Fields, tt.fields)
			}
			for _, f := range tt.fields {
				if resp.Fields[f] == "" {
					t.Errorf("fields[%q] missing in %v", f, resp.Fields)
				}
			}
		})
	}

	assertBookCount(t, srv, 0)
}

func TestCreateBookRejectsMalformedBodies(t *testing.T) {
	srv, _ := newTestServer(t)

	tests := []struct {
		name    string
		body    string
		status  int
		errPart string
	}{
		{"empty body", ``, http.StatusBadRequest, "must not be empty"},
		{"truncated JSON", `{"title":"T"`, http.StatusBadRequest, "malformed JSON"},
		{"invalid JSON", `{title:"T"}`, http.StatusBadRequest, "malformed JSON"},
		{"array", `[{"title":"T","author":"A"}]`, http.StatusBadRequest, "must be a JSON object"},
		{"title wrong type", `{"title":5,"author":"A"}`, http.StatusBadRequest, `"title" must be a string`},
		{"year as string", `{"title":"T","author":"A","year":"1937"}`, http.StatusBadRequest, `"year" must be an integer`},
		{"year fractional", `{"title":"T","author":"A","year":1937.5}`, http.StatusBadRequest, `"year" must be an integer`},
		{"two objects", `{"title":"T","author":"A"}{"title":"U","author":"B"}`, http.StatusBadRequest, "single JSON object"},
		{"too large", `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`, http.StatusRequestEntityTooLarge, "must not exceed"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, srv, http.MethodPost, "/books", tt.body)
			expectStatus(t, rec, tt.status)
			if resp := decodeBody[errorResponse](t, rec); !strings.Contains(resp.Error, tt.errPart) {
				t.Errorf("error = %q, want it to contain %q", resp.Error, tt.errPart)
			}
		})
	}

	assertBookCount(t, srv, 0)
}

func TestGetBook(t *testing.T) {
	srv, _ := newTestServer(t)
	book := createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)

	rec := do(t, srv, http.MethodGet, fmt.Sprintf("/books/%d", book.ID), "")
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got.Title != "Dune" || got.Author != "Frank Herbert" || *got.Year != 1965 {
		t.Errorf("got %+v", got)
	}

	rec = do(t, srv, http.MethodGet, "/books/9999", "")
	expectStatus(t, rec, http.StatusNotFound)
	if resp := decodeBody[errorResponse](t, rec); resp.Error != "book not found" {
		t.Errorf("error = %q, want %q", resp.Error, "book not found")
	}

	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		rec = do(t, srv, http.MethodGet, "/books/"+id, "")
		expectStatus(t, rec, http.StatusBadRequest)
		decodeBody[errorResponse](t, rec)
	}
}

func TestListBooks(t *testing.T) {
	srv, _ := newTestServer(t)

	// An empty collection is an empty JSON array, not null.
	rec := do(t, srv, http.MethodGet, "/books", "")
	expectStatus(t, rec, http.StatusOK)
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty list body = %q, want []", body)
	}

	hobbit := createBook(t, srv, `{"title":"The Hobbit","author":"J.R.R. Tolkien"}`)
	earthsea := createBook(t, srv, `{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin"}`)
	silmarillion := createBook(t, srv, `{"title":"The Silmarillion","author":"J.R.R. Tolkien"}`)

	tests := []struct {
		query string
		want  []int64
	}{
		{"", []int64{hobbit.ID, earthsea.ID, silmarillion.ID}},
		{"?author=" + url.QueryEscape("J.R.R. Tolkien"), []int64{hobbit.ID, silmarillion.ID}},
		{"?author=tolkien", []int64{hobbit.ID, silmarillion.ID}},
		{"?author=LE%20GUIN", []int64{earthsea.ID}},
		{"?author=", []int64{hobbit.ID, earthsea.ID, silmarillion.ID}},
		{"?author=Asimov", nil},
		{"?author=%25", nil},
	}
	for _, tt := range tests {
		t.Run(tt.query, func(t *testing.T) {
			rec := do(t, srv, http.MethodGet, "/books"+tt.query, "")
			expectStatus(t, rec, http.StatusOK)
			books := decodeBody[[]Book](t, rec)
			if books == nil {
				t.Fatalf("body = %q, want a JSON array", rec.Body.String())
			}
			var got []int64
			for _, b := range books {
				got = append(got, b.ID)
			}
			if fmt.Sprint(got) != fmt.Sprint(tt.want) {
				t.Errorf("ids = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestUpdateBook(t *testing.T) {
	srv, st := newTestServer(t)
	book := createBook(t, srv, `{"title":"Foundaton","author":"Isaac Asimov","year":1950,"isbn":"0-306-40615-2"}`)
	path := fmt.Sprintf("/books/%d", book.ID)

	later := book.CreatedAt.Add(time.Hour)
	st.now = func() time.Time { return later }

	rec := do(t, srv, http.MethodPut, path, `{"title":"Foundation","author":"Isaac Asimov","year":1951,"isbn":"9780134685991"}`)
	expectStatus(t, rec, http.StatusOK)
	updated := decodeBody[Book](t, rec)
	if updated.ID != book.ID || updated.Title != "Foundation" || *updated.Year != 1951 || *updated.ISBN != "9780134685991" {
		t.Errorf("updated book = %+v", updated)
	}
	if !updated.CreatedAt.Equal(book.CreatedAt) {
		t.Errorf("created_at changed from %v to %v", book.CreatedAt, updated.CreatedAt)
	}
	if !updated.UpdatedAt.Equal(later) {
		t.Errorf("updated_at = %v, want %v", updated.UpdatedAt, later)
	}

	// The change is persisted.
	rec = do(t, srv, http.MethodGet, path, "")
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got.Title != "Foundation" || !got.UpdatedAt.Equal(later) {
		t.Errorf("GET after PUT = %+v", got)
	}

	// PUT replaces the whole resource: omitted optional fields are cleared.
	rec = do(t, srv, http.MethodPut, path, `{"title":"Foundation","author":"Isaac Asimov"}`)
	expectStatus(t, rec, http.StatusOK)
	if got := decodeBody[Book](t, rec); got.Year != nil || got.ISBN != nil {
		t.Errorf("year/isbn = %v/%v, want both cleared", got.Year, got.ISBN)
	}

	// Invalid input is rejected and leaves the book untouched.
	rec = do(t, srv, http.MethodPut, path, `{"title":"","author":"Isaac Asimov"}`)
	expectStatus(t, rec, http.StatusBadRequest)
	if resp := decodeBody[errorResponse](t, rec); resp.Fields["title"] == "" {
		t.Errorf("fields = %v, want title error", resp.Fields)
	}
	rec = do(t, srv, http.MethodGet, path, "")
	if got := decodeBody[Book](t, rec); got.Title != "Foundation" {
		t.Errorf("title after rejected update = %q", got.Title)
	}

	rec = do(t, srv, http.MethodPut, "/books/9999", `{"title":"T","author":"A"}`)
	expectStatus(t, rec, http.StatusNotFound)

	rec = do(t, srv, http.MethodPut, "/books/abc", `{"title":"T","author":"A"}`)
	expectStatus(t, rec, http.StatusBadRequest)
}

func TestDuplicateISBNConflicts(t *testing.T) {
	srv, _ := newTestServer(t)
	first := createBook(t, srv, `{"title":"First","author":"A","isbn":"0-306-40615-2"}`)
	second := createBook(t, srv, `{"title":"Second","author":"B","isbn":"9780306406157"}`)

	// Same ISBN written differently is still a duplicate.
	rec := do(t, srv, http.MethodPost, "/books", `{"title":"Copy","author":"C","isbn":"0306406152"}`)
	expectStatus(t, rec, http.StatusConflict)
	decodeBody[errorResponse](t, rec)

	rec = do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", second.ID), `{"title":"Second","author":"B","isbn":"0306406152"}`)
	expectStatus(t, rec, http.StatusConflict)

	// Re-saving a book with its own ISBN is not a conflict.
	rec = do(t, srv, http.MethodPut, fmt.Sprintf("/books/%d", first.ID), `{"title":"First, revised","author":"A","isbn":"0306406152"}`)
	expectStatus(t, rec, http.StatusOK)

	assertBookCount(t, srv, 2)
}

func TestDeleteBook(t *testing.T) {
	srv, _ := newTestServer(t)
	book := createBook(t, srv, `{"title":"Neuromancer","author":"William Gibson"}`)
	path := fmt.Sprintf("/books/%d", book.ID)

	rec := do(t, srv, http.MethodDelete, path, "")
	expectStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has body %q", rec.Body.String())
	}

	expectStatus(t, do(t, srv, http.MethodGet, path, ""), http.StatusNotFound)
	expectStatus(t, do(t, srv, http.MethodDelete, path, ""), http.StatusNotFound)
	expectStatus(t, do(t, srv, http.MethodDelete, "/books/xyz", ""), http.StatusBadRequest)
	assertBookCount(t, srv, 0)

	// IDs of deleted books are not reused.
	next := createBook(t, srv, `{"title":"Count Zero","author":"William Gibson"}`)
	if next.ID == book.ID {
		t.Errorf("new book reused deleted id %d", book.ID)
	}
}

func TestUnmatchedRoutesReturnJSON(t *testing.T) {
	srv, _ := newTestServer(t)

	rec := do(t, srv, http.MethodGet, "/nope", "")
	expectStatus(t, rec, http.StatusNotFound)
	if resp := decodeBody[errorResponse](t, rec); resp.Error != "resource not found" {
		t.Errorf("error = %q", resp.Error)
	}

	rec = do(t, srv, http.MethodPatch, "/books/1", `{"title":"T"}`)
	expectStatus(t, rec, http.StatusMethodNotAllowed)
	if resp := decodeBody[errorResponse](t, rec); resp.Error != "method not allowed" {
		t.Errorf("error = %q", resp.Error)
	}
	allow := rec.Header().Get("Allow")
	for _, m := range []string{"GET", "PUT", "DELETE"} {
		if !strings.Contains(allow, m) {
			t.Errorf("Allow = %q, missing %s", allow, m)
		}
	}

	expectStatus(t, do(t, srv, http.MethodDelete, "/books", ""), http.StatusMethodNotAllowed)
	expectStatus(t, do(t, srv, http.MethodPost, "/health", ""), http.StatusMethodNotAllowed)
}

// TestRunServesOverHTTP starts the real server on a random port and drives it
// with concurrent clients, then checks that it shuts down cleanly.
func TestRunServesOverHTTP(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	dbPath := filepath.Join(t.TempDir(), "books.db")
	ready := make(chan string, 1)
	done := make(chan error, 1)
	getenv := func(string) string { return "" }
	go func() {
		done <- run(ctx, []string{"-addr", "127.0.0.1:0", "-db", dbPath}, getenv, slog.New(slog.DiscardHandler), ready)
	}()

	var base string
	select {
	case addr := <-ready:
		base = "http://" + addr
	case err := <-done:
		t.Fatalf("run exited early: %v", err)
	case <-time.After(10 * time.Second):
		t.Fatal("server did not start")
	}

	resp, err := http.Get(base + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("GET /health status = %d", resp.StatusCode)
	}

	const n = 25
	var wg sync.WaitGroup
	errs := make(chan error, n)
	for i := range n {
		wg.Go(func() {
			body := fmt.Sprintf(`{"title":"Book %d","author":"Author %d"}`, i, i%3)
			resp, err := http.Post(base+"/books", "application/json", strings.NewReader(body))
			if err != nil {
				errs <- err
				return
			}
			defer resp.Body.Close()
			if resp.StatusCode != http.StatusCreated {
				b, _ := io.ReadAll(resp.Body)
				errs <- fmt.Errorf("POST status %d: %s", resp.StatusCode, b)
			}
		})
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		t.Error(err)
	}

	resp, err = http.Get(base + "/books?author=" + url.QueryEscape("Author 1"))
	if err != nil {
		t.Fatalf("GET /books: %v", err)
	}
	var books []Book
	err = json.NewDecoder(resp.Body).Decode(&books)
	resp.Body.Close()
	if err != nil {
		t.Fatalf("decode list: %v", err)
	}
	if len(books) != 8 { // i%3 == 1 for i in [0,25): 1,4,...,22
		t.Errorf("filtered list has %d books, want 8", len(books))
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Errorf("run returned %v, want nil after shutdown", err)
		}
	case <-time.After(15 * time.Second):
		t.Fatal("server did not shut down")
	}
}

func assertBookCount(t *testing.T, h http.Handler, want int) {
	t.Helper()
	rec := do(t, h, http.MethodGet, "/books", "")
	expectStatus(t, rec, http.StatusOK)
	if got := len(decodeBody[[]Book](t, rec)); got != want {
		t.Errorf("collection has %d books, want %d", got, want)
	}
}
