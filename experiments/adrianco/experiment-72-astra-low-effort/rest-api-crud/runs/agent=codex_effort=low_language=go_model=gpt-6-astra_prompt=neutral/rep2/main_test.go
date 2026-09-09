package main

import (
	"encoding/json"
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
		t.Fatalf("%s %s: got %d want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 {
		if w.Header().Get("Content-Type") != "application/json" || !json.Valid(w.Body.Bytes()) {
			t.Fatalf("expected JSON response: %s", w.Body.String())
		}
	}
	return w
}
func TestBookLifecycle(t *testing.T) {
	h := testAPI(t)
	w := request(t, h, "GET", "/books", "", 200)
	if strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal(w.Body.String())
	}
	w = request(t, h, "POST", "/books", `{"title":" Dune ","author":" Frank Herbert ","year":1965,"isbn":"9780441172719"}`, 201)
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatal(err)
	}
	if created.ID <= 0 || created.Title != "Dune" || created.Author != "Frank Herbert" || created.Year != 1965 || created.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", created)
	}
	path := w.Header().Get("Location")
	if path == "" {
		t.Fatal("missing Location")
	}
	w = request(t, h, "GET", path, "", 200)
	var fetched Book
	_ = json.Unmarshal(w.Body.Bytes(), &fetched)
	if fetched != created {
		t.Fatalf("got %+v want %+v", fetched, created)
	}
	request(t, h, "PUT", path, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"updated"}`, 200)
	w = request(t, h, "GET", path, "", 200)
	_ = json.Unmarshal(w.Body.Bytes(), &fetched)
	if fetched.ID != created.ID || fetched.Title != "Dune Messiah" || fetched.Year != 1969 || fetched.ISBN != "updated" {
		t.Fatalf("update failed: %+v", fetched)
	}
	w = request(t, h, "DELETE", path, "", 204)
	if w.Body.Len() != 0 {
		t.Fatal("204 must be empty")
	}
	request(t, h, "GET", path, "", 404)
	request(t, h, "DELETE", path, "", 404)
	request(t, h, "PUT", path, `{"title":"T","author":"A"}`, 404)
}
func TestAuthorFilter(t *testing.T) {
	h := testAPI(t)
	for _, body := range []string{`{"title":"One","author":"A"}`, `{"title":"Two","author":"B"}`, `{"title":"Three","author":"A"}`} {
		request(t, h, "POST", "/books", body, 201)
	}
	for _, tc := range []struct {
		path  string
		count int
	}{{"/books", 3}, {"/books?author=A", 2}, {"/books?author=a", 0}, {"/books?author=", 0}, {"/books?author=%27%20OR%201%3D1--", 0}} {
		w := request(t, h, "GET", tc.path, "", 200)
		var books []Book
		_ = json.Unmarshal(w.Body.Bytes(), &books)
		if len(books) != tc.count {
			t.Fatalf("%s: %+v", tc.path, books)
		}
		for i, b := range books {
			if tc.path == "/books?author=A" && b.Author != "A" {
				t.Fatal(b)
			}
			if i > 0 && b.ID <= books[i-1].ID {
				t.Fatal("unordered books")
			}
		}
	}
}
func TestValidation(t *testing.T) {
	h := testAPI(t)
	request(t, h, "POST", "/books", `{"title":"Original","author":"Author"}`, 201)
	invalid := []string{`{}`, `null`, `[]`, `{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `{"title":"T","author":"\t"}`, `{"title":"T","author":"A","year":"wrong"}`, `{"title":"T","author":"A","extra":1}`, `{"title":"T","author":"A"} {}`, `{`, "", `{"title":"` + strings.Repeat("x", 1<<20) + `","author":"A"}`}
	for _, method := range []string{"POST", "PUT"} {
		path := "/books"
		if method == "PUT" {
			path += "/1"
		}
		for i, body := range invalid {
			t.Run(method+"/"+string(rune('A'+i)), func(t *testing.T) { request(t, h, method, path, body, 400) })
		}
	}
	w := request(t, h, "GET", "/books", "", 200)
	var books []Book
	_ = json.Unmarshal(w.Body.Bytes(), &books)
	if len(books) != 1 || books[0].Title != "Original" {
		t.Fatalf("invalid writes modified data: %+v", books)
	}
}
func TestRoutingAndHealth(t *testing.T) {
	h := testAPI(t)
	request(t, h, "GET", "/health", "", 200)
	for _, path := range []string{"/books/nope", "/books/0", "/books/-1", "/books/9223372036854775808"} {
		request(t, h, "GET", path, "", 400)
	}
	for _, path := range []string{"/unknown", "/books/1/extra", "/books/", "/books/999"} {
		request(t, h, "GET", path, "", 404)
	}
	for _, path := range []string{"/books", "/books/1", "/health"} {
		w := request(t, h, "PATCH", path, "", 405)
		if w.Header().Get("Allow") == "" {
			t.Fatal("missing Allow")
		}
	}
	db, err := openDB(filepath.Join(t.TempDir(), "closed.db"))
	if err != nil {
		t.Fatal(err)
	}
	db.Close()
	request(t, newHandler(db), "GET", "/health", "", 503)
}
func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persistent.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	request(t, newHandler(db), "POST", "/books", `{"title":"Persistent","author":"Writer"}`, 201)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	db, err = openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	w := request(t, newHandler(db), "GET", "/books/1", "", 200)
	var book Book
	_ = json.Unmarshal(w.Body.Bytes(), &book)
	if book.Title != "Persistent" || book.Author != "Writer" {
		t.Fatalf("not persisted: %+v", book)
	}
}
