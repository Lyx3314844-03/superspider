package downloader

import (
	"fmt"
	"net"
	"net/netip"
	"net/url"
	"strings"
)

var blockedHosts = map[string]struct{}{
	"localhost":                {},
	"metadata.google.internal": {},
}

var blockedIPs = []netip.Prefix{
	netip.MustParsePrefix("127.0.0.0/8"),
	netip.MustParsePrefix("10.0.0.0/8"),
	netip.MustParsePrefix("172.16.0.0/12"),
	netip.MustParsePrefix("192.168.0.0/16"),
	netip.MustParsePrefix("169.254.0.0/16"),
	netip.MustParsePrefix("224.0.0.0/4"),
	netip.MustParsePrefix("::1/128"),
	netip.MustParsePrefix("fc00::/7"),
	netip.MustParsePrefix("fe80::/10"),
}

var lookupIP = net.LookupIP

func IsSafeURL(rawURL string) bool {
	parsed, err := url.Parse(strings.TrimSpace(rawURL))
	if err != nil {
		return false
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return false
	}
	host := strings.TrimSpace(parsed.Hostname())
	if host == "" {
		return false
	}
	if _, blocked := blockedHosts[strings.ToLower(host)]; blocked {
		return false
	}
	if host == "169.254.169.254" || host == "168.63.129.16" {
		return false
	}
	if ip, err := netip.ParseAddr(host); err == nil {
		return !isBlockedIP(ip)
	}
	ips, err := lookupIP(host)
	if err != nil || len(ips) == 0 {
		return false
	}
	for _, resolved := range ips {
		addr, ok := netip.AddrFromSlice(resolved)
		if !ok {
			return false
		}
		if isBlockedIP(addr.Unmap()) {
			return false
		}
	}
	return true
}

func ValidateSafeURL(rawURL string) error {
	if !IsSafeURL(rawURL) {
		return fmt.Errorf("blocked by SSRF protection: %s", rawURL)
	}
	return nil
}

func isBlockedIP(ip netip.Addr) bool {
	for _, prefix := range blockedIPs {
		if prefix.Contains(ip) {
			return true
		}
	}
	return false
}

func (d *HTTPDownloader) DownloadSafe(req *Request) *Response {
	if err := ValidateSafeURL(req.URL); err != nil {
		return &Response{
			URL:   req.URL,
			Error: err,
		}
	}
	return d.Download(req)
}

func ResolveHostIP(host string) ([]net.IP, error) {
	return net.LookupIP(host)
}
