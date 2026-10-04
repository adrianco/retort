package main

import (
	"database/sql"
	"encoding/json"
	_ "github.com/mattn/go-sqlite3"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

func newTestAPI(t *testing.T) http.Handler {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	api, err := NewAPI(db)
	if err != nil {
		t.Fatal(err)
	}
	return api
}
func request(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	h := newTestAPI(t)
	created := request(h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status=%d body=%s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("unexpected book: %+v", b)
	}
	got := request(h, http.MethodGet, "/books/"+itoa(b.ID), "")
	if got.Code != http.StatusOK {
		t.Fatalf("get status=%d body=%s", got.Code, got.Body)
	}
}

func TestListFiltersAuthorAndValidation(t *testing.T) {
	h := newTestAPI(t)
	request(h, http.MethodPost, "/books", `{"title":"One","author":"A"}`)
	request(h, http.MethodPost, "/books", `{"title":"Two","author":"B"}`)
	w := request(h, http.MethodGet, "/books?author=A", "")
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
		t.Fatal(err)
	}
	if w.Code != http.StatusOK || len(books) != 1 || books[0].Author != "A" {
		t.Fatalf("status=%d books=%+v", w.Code, books)
	}
	bad := request(h, http.MethodPost, "/books", `{"title":"Missing author"}`)
	if bad.Code != http.StatusBadRequest {
		t.Fatalf("validation status=%d", bad.Code)
	}
}

func TestUpdateDeleteNotFoundAndHealth(t *testing.T) {
	h := newTestAPI(t)
	created := request(h, http.MethodPost, "/books", `{"title":"Old","author":"Writer"}`)
	var b Book
	_ = json.Unmarshal(created.Body.Bytes(), &b)
	id := itoa(b.ID)
	updated := request(h, http.MethodPut, "/books/"+id, `{"title":"New","author":"Writer","year":2020}`)
	if updated.Code != http.StatusOK {
		t.Fatalf("update status=%d", updated.Code)
	}
	del := request(h, http.MethodDelete, "/books/"+id, "")
	if del.Code != http.StatusNoContent {
		t.Fatalf("delete status=%d", del.Code)
	}
	missing := request(h, http.MethodGet, "/books/"+id, "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing status=%d", missing.Code)
	}
	if health := request(h, http.MethodGet, "/health", ""); health.Code != http.StatusOK {
		t.Fatalf("health status=%d", health.Code)
	}
}

func itoa(n int64) string { return strconv.FormatInt(n, 10) }
