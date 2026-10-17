package bookapi

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

func newTestAPI(t *testing.T) http.Handler {
	t.Helper()
	store, err := OpenStore(filepath.Join(t.TempDir(), "api.db"))
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewHandler(store)
}

// do sends a request through h and returns the recorded response.
func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r io.Reader
	if body != "" {
		r = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, path, r)
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// decode unmarshals the response body into v, failing the test on error.
func decode(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.Unmarshal(rec.Body.Bytes(), v); err != nil {
		t.Fatalf("decode %q: %v", rec.Body.String(), err)
	}
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func createBook(t *testing.T, h http.Handler, body string) Book {
	t.Helper()
	rec := do(t, h, http.MethodPost, "/books", body)
	expectStatus(t, rec, http.StatusCreated)
	var b Book
	decode(t, rec, &b)
	return b
}

func TestHealth(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)

	var body map[string]string
	decode(t, rec, &body)
	if body["status"] != "ok" {
		t.Errorf("health body = %v, want status ok", body)
	}
}

func TestCreateBook(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodPost, "/books",
		`{"title":"  Dune ","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}`)
	expectStatus(t, rec, http.StatusCreated)

	var b Book
	decode(t, rec, &b)
	if b.ID == 0 {
		t.Error("created book has no id")
	}
	if b.Title != "Dune" {
		t.Errorf("title = %q, want trimmed %q", b.Title, "Dune")
	}
	if b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Errorf("created book = %+v", b)
	}
	if loc, want := rec.Header().Get("Location"), "/books/"+itoa(b.ID); loc != want {
		t.Errorf("Location = %q, want %q", loc, want)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodPost, "/books", `{"year":1965}`)
	expectStatus(t, rec, http.StatusBadRequest)

	var body struct {
		Error  string            `json:"error"`
		Fields map[string]string `json:"fields"`
	}
	decode(t, rec, &body)
	if body.Fields["title"] == "" || body.Fields["author"] == "" {
		t.Errorf("expected title and author field errors, got %v", body.Fields)
	}

	// Nothing should have been stored.
	list := do(t, h, http.MethodGet, "/books", "")
	var books []Book
	decode(t, list, &books)
	if len(books) != 0 {
		t.Errorf("invalid create stored %d books", len(books))
	}
}

func TestMalformedRequestBodies(t *testing.T) {
	h := newTestAPI(t)

	tests := map[string]string{
		"invalid JSON":  `{"title":`,
		"unknown field": `{"title":"T","author":"A","pages":300}`,
		"empty body":    ``,
		"trailing data": `{"title":"T","author":"A"} {}`,
		"wrong type":    `{"title":"T","author":"A","year":"1965"}`,
		"array instead": `[{"title":"T","author":"A"}]`,
	}
	for name, body := range tests {
		t.Run(name, func(t *testing.T) {
			rec := do(t, h, http.MethodPost, "/books", body)
			expectStatus(t, rec, http.StatusBadRequest)
		})
	}
}

func TestRequestBodyTooLarge(t *testing.T) {
	h := newTestAPI(t)

	huge := `{"title":"` + strings.Repeat("a", maxBodyBytes+1) + `","author":"A"}`
	rec := do(t, h, http.MethodPost, "/books", huge)
	expectStatus(t, rec, http.StatusBadRequest)
}

func TestGetBook(t *testing.T) {
	h := newTestAPI(t)
	created := createBook(t, h, `{"title":"Emma","author":"Jane Austen","year":1815}`)

	rec := do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	expectStatus(t, rec, http.StatusOK)

	var got Book
	decode(t, rec, &got)
	if got != created {
		t.Errorf("GET = %+v, want %+v", got, created)
	}

	expectStatus(t, do(t, h, http.MethodGet, "/books/9999", ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodGet, "/books/abc", ""), http.StatusBadRequest)
	expectStatus(t, do(t, h, http.MethodGet, "/books/0", ""), http.StatusBadRequest)
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	h := newTestAPI(t)

	// Empty collection returns [] rather than null.
	rec := do(t, h, http.MethodGet, "/books", "")
	expectStatus(t, rec, http.StatusOK)
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Errorf("empty list body = %q, want []", rec.Body.String())
	}

	createBook(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	createBook(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	createBook(t, h, `{"title":"Children of Dune","author":"Frank Herbert"}`)

	var all []Book
	decode(t, do(t, h, http.MethodGet, "/books", ""), &all)
	if len(all) != 3 {
		t.Fatalf("list all = %d books, want 3", len(all))
	}

	var filtered []Book
	rec = do(t, h, http.MethodGet, "/books?author=Frank%20Herbert", "")
	expectStatus(t, rec, http.StatusOK)
	decode(t, rec, &filtered)
	if len(filtered) != 2 {
		t.Fatalf("filtered = %d books, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("filtered result author = %q", b.Author)
		}
	}
}

func TestUpdateBook(t *testing.T) {
	h := newTestAPI(t)
	created := createBook(t, h, `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	path := "/books/" + itoa(created.ID)

	rec := do(t, h, http.MethodPut, path, `{"title":"Dune","author":"F. Herbert","year":1966}`)
	expectStatus(t, rec, http.StatusOK)

	var updated Book
	decode(t, rec, &updated)
	if updated.ID != created.ID || updated.Author != "F. Herbert" || updated.Year != 1966 {
		t.Errorf("PUT returned %+v", updated)
	}
	// PUT replaces the whole resource, so omitted optional fields are cleared.
	if updated.ISBN != "" {
		t.Errorf("isbn = %q, want cleared", updated.ISBN)
	}

	var got Book
	decode(t, do(t, h, http.MethodGet, path, ""), &got)
	if got != updated {
		t.Errorf("GET after PUT = %+v, want %+v", got, updated)
	}

	rec = do(t, h, http.MethodPut, path, `{"year":1966}`)
	expectStatus(t, rec, http.StatusBadRequest)

	expectStatus(t, do(t, h, http.MethodPut, "/books/9999", `{"title":"T","author":"A"}`), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodPut, "/books/abc", `{"title":"T","author":"A"}`), http.StatusBadRequest)
}

func TestDeleteBook(t *testing.T) {
	h := newTestAPI(t)
	created := createBook(t, h, `{"title":"Emma","author":"Jane Austen"}`)
	path := "/books/" + itoa(created.ID)

	rec := do(t, h, http.MethodDelete, path, "")
	expectStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", rec.Body.String())
	}

	expectStatus(t, do(t, h, http.MethodGet, path, ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodDelete, path, ""), http.StatusNotFound)
	expectStatus(t, do(t, h, http.MethodDelete, "/books/abc", ""), http.StatusBadRequest)
}

func TestErrorsAreJSON(t *testing.T) {
	h := newTestAPI(t)

	rec := do(t, h, http.MethodGet, "/books/9999", "")
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("404 Content-Type = %q", ct)
	}
	var body map[string]string
	decode(t, rec, &body)
	if body["error"] == "" {
		t.Errorf("error body = %s, want {\"error\": ...}", rec.Body.String())
	}
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}
