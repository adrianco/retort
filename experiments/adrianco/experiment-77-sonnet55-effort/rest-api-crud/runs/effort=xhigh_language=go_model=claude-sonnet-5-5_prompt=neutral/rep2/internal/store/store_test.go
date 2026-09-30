package store

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"testing"
)

func intPtr(v int) *int { return &v }

func openMemory(t *testing.T) *Store {
	t.Helper()
	s, err := Open(":memory:")
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestCreateGetRoundTrip(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()

	created, err := s.Create(ctx, Input{Title: "1984", Author: "George Orwell", Year: intPtr(1949), ISBN: "9780451524935"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("Create returned zero ID")
	}

	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Title != "1984" || got.Author != "George Orwell" || got.ISBN != "9780451524935" ||
		got.Year == nil || *got.Year != 1949 {
		t.Errorf("Get returned %+v", got)
	}
}

func TestNilYearIsStoredAsNull(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()

	created, err := s.Create(ctx, Input{Title: "Untitled", Author: "Anon"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	got, err := s.Get(ctx, created.ID)
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.Year != nil {
		t.Errorf("Year = %d, want nil", *got.Year)
	}
}

func TestListFiltersByAuthorCaseInsensitively(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()
	for _, in := range []Input{
		{Title: "1984", Author: "George Orwell"},
		{Title: "Emma", Author: "Jane Austen"},
		{Title: "Animal Farm", Author: "George Orwell"},
	} {
		if _, err := s.Create(ctx, in); err != nil {
			t.Fatalf("Create: %v", err)
		}
	}

	all, err := s.List(ctx, "")
	if err != nil || len(all) != 3 {
		t.Fatalf("List(\"\") = %d books, err %v; want 3", len(all), err)
	}

	orwell, err := s.List(ctx, "george ORWELL")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(orwell) != 2 || orwell[0].Title != "1984" || orwell[1].Title != "Animal Farm" {
		t.Errorf("List(orwell) = %+v", orwell)
	}

	none, err := s.List(ctx, "Orwell") // exact match, not substring
	if err != nil || none == nil || len(none) != 0 {
		t.Errorf("List(partial) = %#v, err %v; want empty non-nil slice", none, err)
	}
}

func TestUpdateReplacesFields(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()
	created, _ := s.Create(ctx, Input{Title: "Old", Author: "A", Year: intPtr(2000), ISBN: "1"})

	updated, err := s.Update(ctx, created.ID, Input{Title: "New", Author: "B"})
	if err != nil {
		t.Fatalf("Update: %v", err)
	}
	if updated.ID != created.ID || updated.Title != "New" || updated.Author != "B" ||
		updated.Year != nil || updated.ISBN != "" {
		t.Errorf("Update returned %+v", updated)
	}

	got, _ := s.Get(ctx, created.ID)
	if got.Title != "New" || got.Year != nil {
		t.Errorf("Get after Update returned %+v", got)
	}
}

func TestDeleteRemovesBook(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()
	created, _ := s.Create(ctx, Input{Title: "T", Author: "A"})

	if err := s.Delete(ctx, created.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if _, err := s.Get(ctx, created.ID); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get after Delete: err = %v, want ErrNotFound", err)
	}
}

func TestMissingBookReturnsErrNotFound(t *testing.T) {
	s := openMemory(t)
	ctx := context.Background()

	if _, err := s.Get(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get: err = %v, want ErrNotFound", err)
	}
	if _, err := s.Update(ctx, 42, Input{Title: "T", Author: "A"}); !errors.Is(err, ErrNotFound) {
		t.Errorf("Update: err = %v, want ErrNotFound", err)
	}
	if err := s.Delete(ctx, 42); !errors.Is(err, ErrNotFound) {
		t.Errorf("Delete: err = %v, want ErrNotFound", err)
	}
}

func TestDataPersistsAcrossReopen(t *testing.T) {
	// The directory name contains characters that are special in SQLite URIs.
	path := filepath.Join(t.TempDir(), "a b?c#d%e", "books.db")
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatalf("MkdirAll: %v", err)
	}
	ctx := context.Background()

	s, err := Open(path)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	created, err := s.Create(ctx, Input{Title: "Persistent", Author: "A"})
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if err := s.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	s, err = Open(path)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer s.Close()
	got, err := s.Get(ctx, created.ID)
	if err != nil || got.Title != "Persistent" {
		t.Errorf("Get after reopen = %+v, err %v", got, err)
	}
}

func TestConcurrentWrites(t *testing.T) {
	s, err := Open(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	defer s.Close()
	ctx := context.Background()

	const n = 40
	var wg sync.WaitGroup
	errs := make(chan error, n)
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			_, err := s.Create(ctx, Input{Title: fmt.Sprintf("Book %d", i), Author: "A"})
			errs <- err
		}()
	}
	wg.Wait()
	close(errs)
	for err := range errs {
		if err != nil {
			t.Errorf("concurrent Create: %v", err)
		}
	}

	books, err := s.List(ctx, "")
	if err != nil || len(books) != n {
		t.Errorf("List = %d books, err %v; want %d", len(books), err, n)
	}
}

func TestOpenRejectsEmptyPath(t *testing.T) {
	if _, err := Open(""); err == nil {
		t.Error("Open(\"\") succeeded, want error")
	}
}

func TestPing(t *testing.T) {
	s := openMemory(t)
	if err := s.Ping(context.Background()); err != nil {
		t.Errorf("Ping: %v", err)
	}
	s.Close()
	if err := s.Ping(context.Background()); err == nil {
		t.Error("Ping after Close succeeded, want error")
	}
}
