package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestAPI(t *testing.T) *API {
	t.Helper()
	db, err := openDatabase(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return &API{db: db}
}

func request(api *API, method, path, body string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(method, path, bytes.NewBufferString(body))
	w := httptest.NewRecorder()
	api.ServeHTTP(w, r)
	return w
}

func TestCreateAndGetBook(t *testing.T) {
	api := newTestAPI(t)
	created := request(api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`)
	if created.Code != http.StatusCreated {
		t.Fatalf("create status = %d, body=%s", created.Code, created.Body)
	}
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil || b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("unexpected create response: %+v, err=%v", b, err)
	}
	got := request(api, http.MethodGet, "/books/"+jsonNumber(b.ID), "")
	if got.Code != http.StatusOK || !bytes.Contains(got.Body.Bytes(), []byte("Frank Herbert")) {
		t.Fatalf("get status=%d body=%s", got.Code, got.Body)
	}
}

func TestListBooksAuthorFilter(t *testing.T) {
	api := newTestAPI(t)
	request(api, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`)
	request(api, http.MethodPost, "/books", `{"title":"Foundation","author":"Isaac Asimov"}`)
	w := request(api, http.MethodGet, "/books?author=frank%20herbert", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d", w.Code)
	}
	var books []Book
	if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil || len(books) != 1 || books[0].Title != "Dune" {
		t.Fatalf("unexpected filtered books: %+v, err=%v", books, err)
	}
}

func TestUpdateDeleteAndValidation(t *testing.T) {
	api := newTestAPI(t)
	invalid := request(api, http.MethodPost, "/books", `{"title":" ","author":"Writer"}`)
	if invalid.Code != http.StatusBadRequest {
		t.Fatalf("invalid create status=%d", invalid.Code)
	}
	created := request(api, http.MethodPost, "/books", `{"title":"Old","author":"Writer"}`)
	var b Book
	if err := json.Unmarshal(created.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	path := "/books/" + jsonNumber(b.ID)
	updated := request(api, http.MethodPut, path, `{"title":"New","author":"Writer","year":2024}`)
	if updated.Code != http.StatusOK || !bytes.Contains(updated.Body.Bytes(), []byte(`"title":"New"`)) {
		t.Fatalf("update status=%d body=%s", updated.Code, updated.Body)
	}
	deleted := request(api, http.MethodDelete, path, "")
	if deleted.Code != http.StatusNoContent {
		t.Fatalf("delete status=%d", deleted.Code)
	}
	missing := request(api, http.MethodGet, path, "")
	if missing.Code != http.StatusNotFound {
		t.Fatalf("missing get status=%d", missing.Code)
	}
}

func TestHealthCheck(t *testing.T) {
	w := request(newTestAPI(t), http.MethodGet, "/health", "")
	if w.Code != http.StatusOK || !bytes.Contains(w.Body.Bytes(), []byte(`"status":"ok"`)) {
		t.Fatalf("health status=%d body=%s", w.Code, w.Body)
	}
}

func jsonNumber(n int64) string {
	var b bytes.Buffer
	_ = json.NewEncoder(&b).Encode(n)
	return string(bytes.TrimSpace(b.Bytes()))
}
