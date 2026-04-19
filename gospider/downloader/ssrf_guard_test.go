package downloader

import (
	"net"
	"testing"
)

func TestSSRFGuardBlocksUnsafeTargets(t *testing.T) {
	unsafe := []string{
		"http://127.0.0.1",
		"http://localhost",
		"http://169.254.169.254/latest/meta-data",
		"file:///etc/passwd",
	}
	for _, candidate := range unsafe {
		if IsSafeURL(candidate) {
			t.Fatalf("expected unsafe url to be blocked: %s", candidate)
		}
	}
}

func TestSSRFGuardAllowsPublicHTTPSTargets(t *testing.T) {
	safe := []string{
		"https://example.com",
		"http://93.184.216.34",
	}
	for _, candidate := range safe {
		if !IsSafeURL(candidate) {
			t.Fatalf("expected safe url to be allowed: %s", candidate)
		}
	}
}

func TestSSRFGuardBlocksHostnamesResolvingToPrivateIPs(t *testing.T) {
	originalLookup := lookupIP
	lookupIP = func(host string) ([]net.IP, error) {
		return []net.IP{net.ParseIP("10.0.0.5")}, nil
	}
	defer func() {
		lookupIP = originalLookup
	}()

	if IsSafeURL("https://resolver.test/resource") {
		t.Fatal("expected hostname resolving to private IP to be blocked")
	}
}

func TestSSRFGuardAllowsHostnamesResolvingToPublicIPs(t *testing.T) {
	originalLookup := lookupIP
	lookupIP = func(host string) ([]net.IP, error) {
		return []net.IP{net.ParseIP("93.184.216.34")}, nil
	}
	defer func() {
		lookupIP = originalLookup
	}()

	if !IsSafeURL("https://resolver.test/resource") {
		t.Fatal("expected hostname resolving to public IP to be allowed")
	}
}
