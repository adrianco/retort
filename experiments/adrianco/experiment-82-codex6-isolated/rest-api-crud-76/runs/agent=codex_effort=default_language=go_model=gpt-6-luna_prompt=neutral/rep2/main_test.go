package main

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

func testAPI(t *testing.T) (*API, *sql.DB) {
	t.Helper()
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	db.SetMaxOpenConns(1)
	api, err := NewAPI(db)
	if err != nil {
		db.Close()
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return api, db
}

func request(api http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	api.ServeHTTP(w, r)
	return w
}

func TestCreateValidateAndFilterBooks(t *testing.T) {
	api, _ := testAPI(t)
	bad := request(api, http.MethodPost, "/books", `{"title":" ","author":"Ada"}`)
	if bad.Code != http.StatusBadRequest {
		t.Fatalf("empty title: got %d", bad.Code)
	}
	created := request(api, http.MethodPost, "/books", `{"title":"The Go Book","author":"Ada","year":2024,"isbn":"123"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create: got %d: %s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "The Go Book" {
		t.Fatalf("unexpected book: %+v", b)
	}
	request(api, http.MethodPost, "/books", `{"title":"Other","author":"Grace"}`)
	list := request(api, http.MethodGet, "/books?author=Ada", "")
	var books []Book
	if err := json.Unmarshal(list.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if list.Code != http.StatusOK || len(books) != 1 || books[0].Author != "Ada" {
		t.Fatalf("filter response %d: %+v", list.Code, books)
	}
}

func TestGetUpdateDeleteBook(t *testing.T) {
	api, _ := testAPI(t)
	created := request(api, http.MethodPost, "/books", `{"title":"Old","author":"Author"}`)
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	path := "/books/" + strconv.FormatInt(b.ID, 10)
	updated := request(api, http.MethodPut, path, `{"title":"New","author":"Author","year":2020,"isbn":"x"}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update: %d %s", updated.Code, updated.Body)
	}
	got := request(api, http.MethodGet, path, "")
	if got.Code != http.StatusOK || !strings.Contains(got.Body.String(), `"title":"New"`) {
		t.Fatalf("get: %d %s", got.Code, got.Body)
	}
	del := request(api, http.MethodDelete, path, "")
	if del.Code != http.StatusNoContent {
		t.Fatalf("delete: %d", del.Code)
	}
	if missing := request(api, http.MethodGet, path, ""); missing.Code != http.StatusNotFound {
		t.Fatalf("after delete: %d", missing.Code)
	}
}

func TestHealthAndNotFound(t *testing.T) {
	api, _ := testAPI(t)
	if got := request(api, http.MethodGet, "/health", ""); got.Code != http.StatusOK || !strings.Contains(got.Body.String(), "ok") {
		t.Fatalf("health: %d %s", got.Code, got.Body)
	}
	if got := request(api, http.MethodGet, "/books/999", ""); got.Code != http.StatusNotFound {
		t.Fatalf("missing book: %d", got.Code)
	}
}
