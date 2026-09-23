package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func testServer(t *testing.T) http.Handler {
	t.Helper()
	db, err := openDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = db.Close() })
	return newHandler(db)
}

func request(t *testing.T, handler http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	req := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	res := httptest.NewRecorder()
	handler.ServeHTTP(res, req)
	return res
}

func TestCreateGetUpdateDeleteBook(t *testing.T) {
	h := testServer(t)
	created := request(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body = %s", created.Code, created.Body)
	}
	var book Book
	if err := json.Unmarshal(created.Body.Bytes(), &book); err != nil || book.ID == 0 || book.Title != "Dune" {
		t.Fatalf("unexpected created book: %+v, err=%v", book, err)
	}
	path := "/books/" + strconv.FormatInt(book.ID, 10)
	got := request(t, h, http.MethodGet, path, "")
	if got.Code != http.StatusOK || !bytes.Contains(got.Body.Bytes(), []byte(`"author":"Frank Herbert"`)) {
		t.Fatalf("get status = %d, body = %s", got.Code, got.Body)
	}
	updated := request(t, h, http.MethodPut, path, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"x"}`)
	if updated.Code != http.StatusOK || !bytes.Contains(updated.Body.Bytes(), []byte("Dune Messiah")) {
		t.Fatalf("update status = %d, body = %s", updated.Code, updated.Body)
	}
	deleted := request(t, h, http.MethodDelete, path, "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d", deleted.Code)
	}
	missing := request(t, h, http.MethodGet, path, "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("get deleted book status = %d", missing.Code)
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	h := testServer(t)
	for _, body := range []string{
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"Foundation","author":"Isaac Asimov"}`,
	} {
		if res := request(t, h, http.MethodPost, "/books", body); res.Code != http.StatusCreated {
			t.Fatalf("create status = %d, body = %s", res.Code, res.Body)
		}
	}
	res := request(t, h, http.MethodGet, "/books?author=frank%20herbert", "")
	if res.Code != http.StatusOK || bytes.Count(res.Body.Bytes(), []byte(`"id"`)) != 1 || !bytes.Contains(res.Body.Bytes(), []byte("Dune")) {
		t.Fatalf("filtered list status = %d, body = %s", res.Code, res.Body)
	}
}

func TestValidationAndHealth(t *testing.T) {
	h := testServer(t)
	invalid := request(t, h, http.MethodPost, "/books", `{"title":"  ","author":"Someone"}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("invalid create status = %d", invalid.Code)
	}
	health := request(t, h, http.MethodGet, "/health", "")
	if health.Code != http.StatusOK || !bytes.Contains(health.Body.Bytes(), []byte(`"status":"ok"`)) {
		t.Fatalf("health status = %d, body = %s", health.Code, health.Body)
	}
}
