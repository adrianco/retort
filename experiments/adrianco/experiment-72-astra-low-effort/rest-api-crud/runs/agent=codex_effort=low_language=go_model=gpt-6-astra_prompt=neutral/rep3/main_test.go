package main

import (
	"encoding/json"
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
		t.Fatalf("%s %s: status %d, want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && w.Header().Get("Content-Type") != "application/json" {
		t.Fatal("response is not JSON")
	}
	return w
}
func TestCRUD(t *testing.T) {
	a := testAPI(t)
	w := request(t, a, "GET", "/books", "", 200)
	if strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal(w.Body.String())
	}
	w = request(t, a, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`, 201)
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID != 1 || b.Title != "Dune" || b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", b)
	}
	if w.Header().Get("Location") != "/books/1" {
		t.Fatal("missing Location")
	}
	w = request(t, a, "GET", "/books/1", "", 200)
	var got Book
	json.Unmarshal(w.Body.Bytes(), &got)
	if got != b {
		t.Fatalf("got %+v want %+v", got, b)
	}
	w = request(t, a, "PUT", "/books/1", `{"title":"Updated","author":"Someone","year":2020,"isbn":"x"}`, 200)
	json.Unmarshal(w.Body.Bytes(), &got)
	if got.ID != 1 || got.Title != "Updated" || got.Author != "Someone" || got.Year != 2020 || got.ISBN != "x" {
		t.Fatalf("unexpected update: %+v", got)
	}
	w = request(t, a, "GET", "/books/1", "", 200)
	var saved Book
	json.Unmarshal(w.Body.Bytes(), &saved)
	if saved != got {
		t.Fatal("update not saved")
	}
	w = request(t, a, "DELETE", "/books/1", "", 204)
	if w.Body.Len() != 0 {
		t.Fatal("204 has body")
	}
	for _, method := range []string{"GET", "PUT", "DELETE"} {
		request(t, a, method, "/books/1", `{"title":"x","author":"y"}`, 404)
	}
}
func TestAuthorFilter(t *testing.T) {
	a := testAPI(t)
	for _, body := range []string{`{"title":"A","author":"Alice"}`, `{"title":"B","author":"Bob"}`, `{"title":"C","author":"Alice"}`} {
		request(t, a, "POST", "/books", body, 201)
	}
	for _, tc := range []struct {
		path  string
		count int
	}{{"/books", 3}, {"/books?author=Alice", 2}, {"/books?author=alice", 0}, {"/books?author=Nobody", 0}, {"/books?author=%27%20OR%201%3D1--", 0}} {
		w := request(t, a, "GET", tc.path, "", 200)
		var bs []Book
		if err := json.Unmarshal(w.Body.Bytes(), &bs); err != nil {
			t.Fatal(err)
		}
		if len(bs) != tc.count {
			t.Fatalf("%s: got %d books", tc.path, len(bs))
		}
	}
}
func TestValidationAndRouting(t *testing.T) {
	a := testAPI(t)
	request(t, a, "POST", "/books", `{"title":"original","author":"author"}`, 201)
	for _, body := range []string{"", `{`, `null`, `[]`, `{}`, `{"title":"x"}`, `{"author":"x"}`, `{"title":"  ","author":"x"}`, `{"title":"x","author":"\t"}`, `{"title":"x","author":"y","year":"bad"}`, `{"title":"x","author":"y","unknown":1}`, `{"title":"x","author":"y"} {}`, `{"title":"x","author":"y"} garbage`} {
		for _, method := range []string{"POST", "PUT"} {
			path := "/books"
			if method == "PUT" {
				path += "/1"
			}
			request(t, a, method, path, body, 400)
		}
	}
	request(t, a, "POST", "/books", `{"title":"`+strings.Repeat("a", 1<<20)+`","author":"x"}`, 400)
	for _, path := range []string{"/books/nope", "/books/0", "/books/-1", "/books/9223372036854775808"} {
		request(t, a, "GET", path, "", 400)
	}
	request(t, a, "GET", "/unknown", "", 404)
	request(t, a, "GET", "/books/1/extra", "", 404)
	w := request(t, a, "PATCH", "/books/1", "", 405)
	if w.Header().Get("Allow") == "" {
		t.Fatal("missing Allow")
	}
	request(t, a, "DELETE", "/books", "", 405)
	request(t, a, "POST", "/health", "", 405)
	w = request(t, a, "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "original") {
		t.Fatal("invalid update changed book")
	}
}
func TestHealthAndPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persistent.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	a := &API{db: db}
	request(t, a, "GET", "/health", "", 200)
	request(t, a, "POST", "/books", `{"title":"Persistent","author":"Writer"}`, 201)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	request(t, a, "GET", "/health", "", 503)
	db, err = openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	w := request(t, &API{db: db}, "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "Persistent") {
		t.Fatal("book did not persist")
	}
}
