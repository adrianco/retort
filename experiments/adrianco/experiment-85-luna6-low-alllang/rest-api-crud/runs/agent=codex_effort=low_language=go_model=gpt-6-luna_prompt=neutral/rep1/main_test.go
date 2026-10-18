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
	db, err := openDB("file:" + t.Name() + "?mode=memory&cache=shared")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return NewAPI(db)
}

func request(t *testing.T, api *API, method, path string, body any) (int, []byte) {
	t.Helper()
	var data []byte
	if body != nil {
		var err error
		data, err = json.Marshal(body)
		if err != nil {
			t.Fatal(err)
		}
	}
	req := httptest.NewRequest(method, path, bytes.NewReader(data))
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp := httptest.NewRecorder()
	api.ServeHTTP(resp, req)
	return resp.Code, resp.Body.Bytes()
}

func TestCreateGetAndListBooks(t *testing.T) {
	s := newTestAPI(t)
	status, body := request(t, s, http.MethodPost, "/books", Book{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"})
	if status != http.StatusCreated {
		t.Fatalf("create status = %d: %s", status, body)
	}
	var created Book
	if err := json.Unmarshal(body, &created); err != nil {
		t.Fatal(err)
	}
	if created.ID == 0 {
		t.Fatalf("missing ID: %+v", created)
	}
	status, body = request(t, s, http.MethodGet, "/books/1", nil)
	if status != http.StatusOK {
		t.Fatalf("get status = %d: %s", status, body)
	}
	var got Book
	if err := json.Unmarshal(body, &got); err != nil {
		t.Fatal(err)
	}
	if got.Title != "Dune" {
		t.Fatalf("got %+v", got)
	}
	status, body = request(t, s, http.MethodGet, "/books?author=Frank%20Herbert", nil)
	if status != http.StatusOK || !bytes.Contains(body, []byte("Dune")) {
		t.Fatalf("list = %d %s", status, body)
	}
}

func TestValidationAndNotFound(t *testing.T) {
	s := newTestAPI(t)
	status, _ := request(t, s, http.MethodPost, "/books", Book{Title: " ", Author: "Someone"})
	if status != http.StatusBadRequest {
		t.Fatalf("validation status = %d", status)
	}
	status, _ = request(t, s, http.MethodGet, "/books/999", nil)
	if status != http.StatusNotFound {
		t.Fatalf("not found status = %d", status)
	}
}

func TestUpdateDeleteAndHealth(t *testing.T) {
	s := newTestAPI(t)
	status, _ := request(t, s, http.MethodPost, "/books", Book{Title: "Old", Author: "Writer"})
	if status != http.StatusCreated {
		t.Fatal(status)
	}
	status, body := request(t, s, http.MethodPut, "/books/1", Book{Title: "New", Author: "Writer", Year: 2020})
	if status != http.StatusOK || !bytes.Contains(body, []byte("New")) {
		t.Fatalf("update = %d %s", status, body)
	}
	status, _ = request(t, s, http.MethodDelete, "/books/1", nil)
	if status != http.StatusNoContent {
		t.Fatalf("delete status = %d", status)
	}
	status, _ = request(t, s, http.MethodGet, "/health", nil)
	if status != http.StatusOK {
		t.Fatalf("health status = %d", status)
	}
}
