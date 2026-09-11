package main

import (
	"net/url"
	"testing"
)

func TestParseWindow(t *testing.T) {
	for _, value := range []string{"1h", "6h", "24h", "7d", "30d"} {
		if _, err := parseWindow(value); err != nil {
			t.Fatalf("parseWindow(%q) returned error: %v", value, err)
		}
	}
	if _, err := parseWindow("90d"); err == nil {
		t.Fatal("parseWindow accepted an unsupported window")
	}
}

func TestSQLStringEscapesValues(t *testing.T) {
	got := sqlString(`a'b\c`)
	want := `'a\'b\\c'`
	if got != want {
		t.Fatalf("sqlString() = %q, want %q", got, want)
	}
}

func TestParseIntQueryBounds(t *testing.T) {
	values := url.Values{"limit": {"1001"}}
	if _, err := parseIntQuery(values, "limit", 50, 1, 1000); err == nil {
		t.Fatal("parseIntQuery accepted a value above the maximum")
	}
}
