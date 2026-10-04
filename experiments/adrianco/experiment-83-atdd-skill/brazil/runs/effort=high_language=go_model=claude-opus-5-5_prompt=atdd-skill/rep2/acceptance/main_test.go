package acceptance

import (
	"os"
	"testing"

	"brsoccer/acceptance/drivers"
)

func TestMain(m *testing.M) {
	code := m.Run()
	drivers.StopProvidedDataSystem()
	os.Exit(code)
}
