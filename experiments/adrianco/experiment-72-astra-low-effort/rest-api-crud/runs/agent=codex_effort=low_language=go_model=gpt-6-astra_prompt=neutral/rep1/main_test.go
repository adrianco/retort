package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func testAPI(t *testing.T) *API {
	t.Helper()
	db, err := openDB(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return &API{db: db}
}
func request(t *testing.T, a *API, method, path, body string, status int) *httptest.ResponseRecorder {
	t.Helper()
	w := httptest.NewRecorder()
	a.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	if w.Code != status {
		t.Fatalf("%s %s: got %d, want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && w.Header().Get("Content-Type") != "application/json" {
		t.Fatal("missing JSON content type")
	}
	return w
}
func decodeBook(t *testing.T, w *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	return b
}
func TestCRUD(t *testing.T) {
	a := testAPI(t)
	w := request(t, a, "POST", "/books", `{"title":" Dune ","author":" Frank Herbert ","year":1965,"isbn":"9780441172719"}`, 201)
	b := decodeBook(t, w)
	if b.ID != 1 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", b)
	}
	if w.Header().Get("Location") != "/books/1" {
		t.Fatal("missing location")
	}
	if got := decodeBook(t, request(t, a, "GET", "/books/1", "", 200)); got != b {
		t.Fatalf("read mismatch: %+v", got)
	}
	updated := decodeBook(t, request(t, a, "PUT", "/books/1", `{"title":"New","author":"Other","year":2020,"isbn":"abc"}`, 200))
	if updated.ID != 1 || updated.Title != "New" || updated.Author != "Other" || updated.Year != 2020 || updated.ISBN != "abc" {
		t.Fatalf("bad update: %+v", updated)
	}
	if got := decodeBook(t, request(t, a, "GET", "/books/1", "", 200)); got != updated {
		t.Fatal("update not persisted")
	}
	request(t, a, "DELETE", "/books/1", "", 204)
	request(t, a, "GET", "/books/1", "", 404)
	request(t, a, "DELETE", "/books/1", "", 404)
	request(t, a, "PUT", "/books/1", `{"title":"New","author":"Other"}`, 404)
}
func TestListAndFilter(t *testing.T) {
	a := testAPI(t)
	if w := request(t, a, "GET", "/books", "", 200); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal("empty list must be an array")
	}
	for _, author := range []string{"Alice", "Bob", "Alice"} {
		request(t, a, "POST", "/books", `{"title":"Book","author":"`+author+`"}`, 201)
	}
	for _, tc := range []struct {
		path  string
		count int
	}{{"/books", 3}, {"/books?author=Alice", 2}, {"/books?author=alice", 0}, {"/books?author=", 0}, {"/books?author=%27%20OR%201%3D1--", 0}} {
		w := request(t, a, "GET", tc.path, "", 200)
		var books []Book
		if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
			t.Fatal(err)
		}
		if len(books) != tc.count {
			t.Fatalf("%s: got %d books", tc.path, len(books))
		}
	}
}
func TestValidation(t *testing.T) {
	a := testAPI(t)
	bodies := []string{`{}`, `null`, `[]`, `{"title":"x"}`, `{"author":"y"}`, `{"title":" ","author":"y"}`, `{"title":"x","author":"\t"}`, `{"title":"x","author":"y","year":"bad"}`, `{"title":"x","author":"y","extra":1}`, `{"title":"x","author":"y"} {}`, `{`, ``}
	for _, body := range bodies {
		t.Run(body, func(t *testing.T) { request(t, a, "POST", "/books", body, 400) })
	}
	request(t, a, "POST", "/books", `{"title":"`+strings.Repeat("x", 1<<20)+`","author":"y"}`, 413)
	request(t, a, "POST", "/books", `{"title":"valid","author":"valid"}`, 201)
	request(t, a, "PUT", "/books/1", `{"title":"invalid"}`, 400)
	if b := decodeBook(t, request(t, a, "GET", "/books/1", "", 200)); b.Title != "valid" {
		t.Fatal("invalid update changed book")
	}
}
func TestRoutingAndHealth(t *testing.T) {
	a := testAPI(t)
	request(t, a, "GET", "/health", "", 200)
	for _, path := range []string{"/books/abc", "/books/0", "/books/-1", "/books/999999999999999999999"} {
		request(t, a, "GET", path, "", 400)
	}
	request(t, a, "GET", "/books/999", "", 404)
	request(t, a, "GET", "/unknown", "", 404)
	request(t, a, "GET", "/books/1/extra", "", 404)
	for _, path := range []string{"/health", "/books", "/books/1"} {
		w := request(t, a, "PATCH", path, "", 405)
		if w.Header().Get("Allow") == "" {
			t.Fatal("missing Allow header")
		}
	}
	a.db.Close()
	request(t, a, http.MethodGet, "/health", "", 503)
	request(t, a, http.MethodGet, "/books", "", 500)
}
func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persistent.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	request(t, &API{db: db}, "POST", "/books", `{"title":"Persistent","author":"Author"}`, 201)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	db, err = openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	if b := decodeBook(t, request(t, &API{db: db}, "GET", "/books/1", "", 200)); b.Title != "Persistent" {
		t.Fatal("book lost after reopening database")
	}
}
