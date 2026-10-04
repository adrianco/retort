package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func testAPI(t *testing.T) http.Handler {
	t.Helper()
	db, err := openDB(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return newHandler(db)
}
func request(t *testing.T, h http.Handler, method, path, body string, status int) *httptest.ResponseRecorder {
	t.Helper()
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	r.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != status {
		t.Fatalf("%s %s: got %d, want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && (w.Header().Get("Content-Type") != "application/json" || !json.Valid(w.Body.Bytes())) {
		t.Fatalf("expected JSON response: %v %s", w.Header(), w.Body.String())
	}
	return w
}
func TestCRUD(t *testing.T) {
	h := testAPI(t)
	w := request(t, h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`, 201)
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID <= 0 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", b)
	}
	path := fmt.Sprintf("/books/%d", b.ID)
	if w.Header().Get("Location") != path {
		t.Fatal("missing Location")
	}
	got := request(t, h, "GET", path, "", 200)
	if got.Body.String() != w.Body.String() {
		t.Fatal("stored book differs")
	}
	request(t, h, "PUT", path, `{"title":"Updated","author":"New author","year":2020,"isbn":"new"}`, 200)
	got = request(t, h, "GET", path, "", 200)
	json.Unmarshal(got.Body.Bytes(), &b)
	if b.Title != "Updated" || b.Author != "New author" || b.Year != 2020 || b.ISBN != "new" {
		t.Fatalf("update failed: %+v", b)
	}
	if w := request(t, h, "DELETE", path, "", 204); w.Body.Len() != 0 {
		t.Fatal("204 must have no body")
	}
	request(t, h, "GET", path, "", 404)
	request(t, h, "DELETE", path, "", 404)
	request(t, h, "PUT", path, `{"title":"Missing","author":"Nobody"}`, 404)
}
func TestListAndAuthorFilter(t *testing.T) {
	h := testAPI(t)
	if w := request(t, h, "GET", "/books", "", 200); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal("empty collection must be []")
	}
	for _, body := range []string{`{"title":"One","author":"Alice"}`, `{"title":"Two","author":"Bob"}`, `{"title":"Three","author":"Alice"}`} {
		request(t, h, "POST", "/books", body, 201)
	}
	for _, tc := range []struct {
		path  string
		count int
	}{{"/books", 3}, {"/books?author=Alice", 2}, {"/books?author=alice", 0}, {"/books?author=Nobody", 0}, {"/books?author=%27%20OR%201%3D1--", 0}} {
		w := request(t, h, "GET", tc.path, "", 200)
		var books []Book
		if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
			t.Fatal(err)
		}
		if len(books) != tc.count {
			t.Fatalf("%s: got %d books", tc.path, len(books))
		}
		for i, b := range books {
			if i > 0 && b.ID <= books[i-1].ID {
				t.Fatal("books not sorted")
			}
		}
	}
}
func TestValidation(t *testing.T) {
	h := testAPI(t)
	for _, body := range []string{`{}`, `null`, `[]`, `{"title":"x"}`, `{"author":"x"}`, `{"title":"  ","author":"x"}`, `{"title":"x","author":"\n"}`, `{"title":"x","author":"y","year":"bad"}`, `{"title":"x","author":"y","unknown":1}`, `{"title":`, `{"title":"x","author":"y"} {}`} {
		t.Run(body, func(t *testing.T) {
			request(t, h, "POST", "/books", body, 400)
			request(t, h, "PUT", "/books/1", body, 400)
		})
	}
	request(t, h, "POST", "/books", `{"title":"`+strings.Repeat("x", 1<<20)+`","author":"a"}`, 413)
	if w := request(t, h, "GET", "/books", "", 200); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal("invalid requests created books")
	}
}
func TestRoutingAndHealth(t *testing.T) {
	h := testAPI(t)
	request(t, h, "GET", "/health", "", 200)
	for _, path := range []string{"/books/nope", "/books/0", "/books/-1", "/books/999999999999999999999"} {
		request(t, h, "GET", path, "", 400)
	}
	for _, path := range []string{"/unknown", "/books/1/extra", "/books/1"} {
		request(t, h, "GET", path, "", 404)
	}
	for _, path := range []string{"/health", "/books", "/books/1"} {
		w := request(t, h, "PATCH", path, "", 405)
		if w.Header().Get("Allow") == "" {
			t.Fatal("missing Allow")
		}
	}
}
func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	request(t, newHandler(db), "POST", "/books", `{"title":"Persistent","author":"Author"}`, 201)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	db, err = openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	w := request(t, newHandler(db), "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "Persistent") {
		t.Fatal("book did not persist")
	}
	db.Close()
	request(t, newHandler(db), "GET", "/health", "", 503)
}
