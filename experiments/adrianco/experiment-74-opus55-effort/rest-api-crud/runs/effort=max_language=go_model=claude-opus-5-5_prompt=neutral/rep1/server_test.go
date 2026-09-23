package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"reflect"
	"slices"
	"strings"
	"sync"
	"testing"
)

// testAPI is the API served over HTTP from a fresh database.
type testAPI struct {
	srv   *httptest.Server
	store *Store
	logs  *syncBuffer
}

func newTestAPI(t *testing.T) *testAPI {
	t.Helper()
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	logs := &syncBuffer{}
	srv := httptest.NewServer(NewServer(store, slog.New(slog.NewTextHandler(logs, nil))).Handler())
	t.Cleanup(func() {
		srv.Close()
		if t.Failed() {
			t.Logf("server log:\n%s", logs)
		}
	})
	return &testAPI{srv: srv, store: store, logs: logs}
}

// response is an HTTP response with its body already read.
type response struct {
	status int
	header http.Header
	body   []byte
}

// do sends a request to the API. A string body is sent as it is; any other
// non-nil body is sent encoded as JSON.
func (a *testAPI) do(t *testing.T, method, path string, body any) response {
	t.Helper()
	var r io.Reader
	switch body := body.(type) {
	case nil:
	case string:
		r = strings.NewReader(body)
	default:
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("encoding request body: %v", err)
		}
		r = bytes.NewReader(b)
	}
	req, err := http.NewRequestWithContext(t.Context(), method, a.srv.URL+path, r)
	if err != nil {
		t.Fatal(err)
	}
	if r != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	res, err := a.srv.Client().Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, path, err)
	}
	defer res.Body.Close()
	b, err := io.ReadAll(res.Body)
	if err != nil {
		t.Fatalf("%s %s: reading response: %v", method, path, err)
	}
	return response{status: res.StatusCode, header: res.Header, body: b}
}

// createBook adds a book through the API and returns it as created.
func (a *testAPI) createBook(t *testing.T, book map[string]any) Book {
	t.Helper()
	res := a.do(t, http.MethodPost, "/books", book)
	expectStatus(t, res, http.StatusCreated)
	return decode[Book](t, res)
}

// getBook fetches a book through the API.
func (a *testAPI) getBook(t *testing.T, id int64) Book {
	t.Helper()
	res := a.do(t, http.MethodGet, fmt.Sprintf("/books/%d", id), nil)
	expectStatus(t, res, http.StatusOK)
	return decode[Book](t, res)
}

func expectStatus(t *testing.T, res response, want int) {
	t.Helper()
	if res.status != want {
		t.Fatalf("status = %d, want %d; body: %s", res.status, want, res.body)
	}
}

// decode checks that res has a JSON body and unmarshals it into a T.
func decode[T any](t *testing.T, res response) T {
	t.Helper()
	if ct := res.header.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var v T
	if err := json.Unmarshal(res.body, &v); err != nil {
		t.Fatalf("decoding response body %q: %v", res.body, err)
	}
	return v
}

func expectBook(t *testing.T, got, want Book) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Errorf("book = %s, want %s", toJSON(got), toJSON(want))
	}
}

// syncBuffer is a bytes.Buffer that is safe for concurrent use, for
// capturing the log of a running server.
type syncBuffer struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (b *syncBuffer) Write(p []byte) (int, error) {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.Write(p)
}

func (b *syncBuffer) String() string {
	b.mu.Lock()
	defer b.mu.Unlock()
	return b.buf.String()
}

func TestHealth(t *testing.T) {
	api := newTestAPI(t)

	res := api.do(t, http.MethodGet, "/health", nil)
	expectStatus(t, res, http.StatusOK)
	if got := decode[map[string]string](t, res); got["status"] != "ok" {
		t.Errorf("health = %v, want status ok", got)
	}
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	api := newTestAPI(t)
	api.store.Close()

	res := api.do(t, http.MethodGet, "/health", nil)
	expectStatus(t, res, http.StatusServiceUnavailable)
	if got := decode[map[string]string](t, res); got["status"] != "unavailable" {
		t.Errorf("health = %v, want status unavailable", got)
	}
}

func TestCreateBook(t *testing.T) {
	api := newTestAPI(t)

	res := api.do(t, http.MethodPost, "/books", map[string]any{
		"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0-452-28423-4",
	})
	expectStatus(t, res, http.StatusCreated)
	created := decode[Book](t, res)
	if created.ID < 1 {
		t.Errorf("id = %d, want a positive id", created.ID)
	}
	want := Book{ID: created.ID, Title: "Nineteen Eighty-Four", Author: "George Orwell", Year: ptr(1949), ISBN: ptr("978-0-452-28423-4")}
	expectBook(t, created, want)

	// The Location header is the new book's URL.
	location := res.header.Get("Location")
	if wantLocation := fmt.Sprintf("/books/%d", created.ID); location != wantLocation {
		t.Fatalf("Location = %q, want %q", location, wantLocation)
	}
	res = api.do(t, http.MethodGet, location, nil)
	expectStatus(t, res, http.StatusOK)
	expectBook(t, decode[Book](t, res), want)
}

func TestCreateBookWithOnlyRequiredFields(t *testing.T) {
	api := newTestAPI(t)

	res := api.do(t, http.MethodPost, "/books", `{"title": "  Beowulf ", "author": "Unknown\n"}`)
	expectStatus(t, res, http.StatusCreated)

	// Text is trimmed, and the missing optional fields are present as null.
	got := decode[map[string]any](t, res)
	want := map[string]any{"id": got["id"], "title": "Beowulf", "author": "Unknown", "year": nil, "isbn": nil}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("book = %v, want %v", got, want)
	}
}

func TestListBooks(t *testing.T) {
	api := newTestAPI(t)

	// An empty collection is an empty array, not null.
	res := api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusOK)
	if body := strings.TrimSpace(string(res.body)); body != "[]" {
		t.Errorf("body = %s, want []", body)
	}

	var want []Book
	for _, book := range []map[string]any{
		{"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949},
		{"title": "Brave New World", "author": "Aldous Huxley", "isbn": "0-06-085052-3"},
		{"title": "Fahrenheit 451", "author": "Ray Bradbury"},
	} {
		want = append(want, api.createBook(t, book))
	}

	res = api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusOK)
	if got := decode[[]Book](t, res); !reflect.DeepEqual(got, want) {
		t.Errorf("books = %s, want %s", toJSON(got), toJSON(want))
	}
}

func TestListBooksFilteredByAuthor(t *testing.T) {
	api := newTestAPI(t)
	for _, book := range []map[string]any{
		{"title": "Nineteen Eighty-Four", "author": "George Orwell"},
		{"title": "Brave New World", "author": "Aldous Huxley"},
		{"title": "Animal Farm", "author": "George Orwell"},
		{"title": "Germinal", "author": "Émile Zola"},
	} {
		api.createBook(t, book)
	}

	tests := []struct {
		author string
		want   []string // titles, in order
	}{
		{"George Orwell", []string{"Nineteen Eighty-Four", "Animal Farm"}},
		{"george orwell", []string{"Nineteen Eighty-Four", "Animal Farm"}},
		{"Orwell", []string{"Nineteen Eighty-Four", "Animal Farm"}},
		{"  Huxley  ", []string{"Brave New World"}},
		{"ÉMILE", []string{"Germinal"}},
		{"Tolkien", nil},
		{"%", nil}, // matched literally, not as a LIKE wildcard
		{"", []string{"Nineteen Eighty-Four", "Brave New World", "Animal Farm", "Germinal"}},
	}
	for _, tt := range tests {
		t.Run(fmt.Sprintf("author=%q", tt.author), func(t *testing.T) {
			res := api.do(t, http.MethodGet, "/books?"+url.Values{"author": {tt.author}}.Encode(), nil)
			expectStatus(t, res, http.StatusOK)
			var titles []string
			for _, b := range decode[[]Book](t, res) {
				titles = append(titles, b.Title)
			}
			if !slices.Equal(titles, tt.want) {
				t.Errorf("titles = %q, want %q", titles, tt.want)
			}
		})
	}
}

func TestGetBook(t *testing.T) {
	api := newTestAPI(t)
	book := api.createBook(t, map[string]any{"title": "Animal Farm", "author": "George Orwell", "year": 1945})

	expectBook(t, api.getBook(t, book.ID), book)

	res := api.do(t, http.MethodGet, "/books/999", nil)
	expectStatus(t, res, http.StatusNotFound)
	if got := decode[errorResponse](t, res); got.Error != "book not found" {
		t.Errorf("error = %q, want %q", got.Error, "book not found")
	}
}

func TestUpdateBook(t *testing.T) {
	api := newTestAPI(t)
	book := api.createBook(t, map[string]any{"title": "1984", "author": "Orwell", "year": 1950, "isbn": "0451524934"})
	other := api.createBook(t, map[string]any{"title": "Brave New World", "author": "Aldous Huxley"})
	path := fmt.Sprintf("/books/%d", book.ID)

	res := api.do(t, http.MethodPut, path, map[string]any{
		"id":    other.ID, // ignored: the URL says which book to update
		"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949, "isbn": "978-0-452-28423-4",
	})
	expectStatus(t, res, http.StatusOK)
	want := Book{ID: book.ID, Title: "Nineteen Eighty-Four", Author: "George Orwell", Year: ptr(1949), ISBN: ptr("978-0-452-28423-4")}
	expectBook(t, decode[Book](t, res), want)
	expectBook(t, api.getBook(t, book.ID), want)
	expectBook(t, api.getBook(t, other.ID), other)

	// PUT replaces the whole book, so optional fields that are left out are cleared.
	res = api.do(t, http.MethodPut, path, map[string]any{"title": "Nineteen Eighty-Four", "author": "George Orwell"})
	expectStatus(t, res, http.StatusOK)
	want = Book{ID: book.ID, Title: "Nineteen Eighty-Four", Author: "George Orwell"}
	expectBook(t, decode[Book](t, res), want)
	expectBook(t, api.getBook(t, book.ID), want)
}

func TestDeleteBook(t *testing.T) {
	api := newTestAPI(t)
	book := api.createBook(t, map[string]any{"title": "Animal Farm", "author": "George Orwell"})
	other := api.createBook(t, map[string]any{"title": "Brave New World", "author": "Aldous Huxley"})
	path := fmt.Sprintf("/books/%d", book.ID)

	res := api.do(t, http.MethodDelete, path, nil)
	expectStatus(t, res, http.StatusNoContent)
	if len(res.body) != 0 {
		t.Errorf("body = %q, want none", res.body)
	}

	expectStatus(t, api.do(t, http.MethodGet, path, nil), http.StatusNotFound)
	expectStatus(t, api.do(t, http.MethodDelete, path, nil), http.StatusNotFound)

	res = api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusOK)
	if got := decode[[]Book](t, res); !reflect.DeepEqual(got, []Book{other}) {
		t.Errorf("books = %s, want %s", toJSON(got), toJSON([]Book{other}))
	}
}

func TestDeletedBookIDsAreNotReused(t *testing.T) {
	api := newTestAPI(t)
	book := api.createBook(t, map[string]any{"title": "Animal Farm", "author": "George Orwell"})
	expectStatus(t, api.do(t, http.MethodDelete, fmt.Sprintf("/books/%d", book.ID), nil), http.StatusNoContent)

	next := api.createBook(t, map[string]any{"title": "Brave New World", "author": "Aldous Huxley"})
	if next.ID == book.ID {
		t.Errorf("new book got id %d, which belonged to a deleted book", next.ID)
	}
}

func TestConcurrentCreates(t *testing.T) {
	api := newTestAPI(t)

	const n = 25
	var wg sync.WaitGroup
	for i := range n {
		wg.Go(func() {
			body := fmt.Sprintf(`{"title": "Book %d", "author": "Author %d"}`, i, i)
			res, err := api.srv.Client().Post(api.srv.URL+"/books", "application/json", strings.NewReader(body))
			if err != nil {
				t.Error(err)
				return
			}
			res.Body.Close()
			if res.StatusCode != http.StatusCreated {
				t.Errorf("POST /books: status = %d, want %d", res.StatusCode, http.StatusCreated)
			}
		})
	}
	wg.Wait()

	res := api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusOK)
	ids := map[int64]bool{}
	for _, b := range decode[[]Book](t, res) {
		ids[b.ID] = true
	}
	if len(ids) != n {
		t.Errorf("got %d distinct books, want %d", len(ids), n)
	}
}
