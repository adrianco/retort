package main

import (
    "log"
    "net/http"
)

func main() {
    r := NewRouter()
    srv := &http.Server{Addr: ":8080", Handler: r}
    log.Println("Starting server on :8080")
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        log.Fatalf("server failed: %v", err)
    }
}
