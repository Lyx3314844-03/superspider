package nodereverse

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"time"
)

const DefaultBaseURL = "http://localhost:3000"

// NodeReverseClient Node.js 逆向服务客户端
type NodeReverseClient struct {
	BaseURL    string
	HTTPClient *http.Client
}

// NewNodeReverseClient 创建新的逆向客户端
func NewNodeReverseClient(baseURL string) *NodeReverseClient {
	if baseURL == "" {
		baseURL = DefaultBaseURL
	}
	return &NodeReverseClient{
		BaseURL: baseURL,
		HTTPClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// CryptoAnalyzeRequest 加密分析请求
type CryptoAnalyzeRequest struct {
	Code string `json:"code"`
}

// CryptoAnalyzeResponse 加密分析响应
type CryptoType struct {
	Name       string   `json:"name"`
	Confidence float64  `json:"confidence"`
	Modes      []string `json:"modes"`
}

type CryptoAnalysisMetadata struct {
	HasKeyDerivation          bool                     `json:"hasKeyDerivation"`
	HasRandomIV               bool                     `json:"hasRandomIV"`
	DetectedLibraries         []string                 `json:"detectedLibraries,omitempty"`
	DetectedOperations        []string                 `json:"detectedOperations,omitempty"`
	DetectedModes             []string                 `json:"detectedModes,omitempty"`
	NormalizedAlgorithms      []string                 `json:"normalizedAlgorithms,omitempty"`
	AlgorithmAliases          map[string][]string      `json:"algorithmAliases,omitempty"`
	DynamicKeySources         []string                 `json:"dynamicKeySources,omitempty"`
	KeyFlowCandidates         []map[string]interface{} `json:"keyFlowCandidates,omitempty"`
	KeyFlowChains             []map[string]interface{} `json:"keyFlowChains,omitempty"`
	RuntimeAlgorithmSelection []string                 `json:"runtimeAlgorithmSelection,omitempty"`
	ObfuscationLoaders        []string                 `json:"obfuscationLoaders,omitempty"`
	CryptoSinks               []string                 `json:"cryptoSinks,omitempty"`
	ReverseComplexity         string                   `json:"reverseComplexity,omitempty"`
	RiskScore                 int                      `json:"riskScore,omitempty"`
	RecommendedApproach       []string                 `json:"recommendedApproach,omitempty"`
	RequiresASTDataflow       bool                     `json:"requiresASTDataflow,omitempty"`
	RequiresRuntimeExecution  bool                     `json:"requiresRuntimeExecution,omitempty"`
	RequiresLoaderUnpack      bool                     `json:"requiresLoaderUnpack,omitempty"`
}

type CryptoAnalyzeResponse struct {
	Success     bool                   `json:"success"`
	CryptoTypes []CryptoType           `json:"cryptoTypes"`
	Keys        []string               `json:"keys"`
	Ivs         []string               `json:"ivs"`
	Analysis    CryptoAnalysisMetadata `json:"analysis"`
}

// AnalyzeCrypto 分析代码中的加密算法
func (c *NodeReverseClient) AnalyzeCrypto(code string) (*CryptoAnalyzeResponse, error) {
	reqBody := CryptoAnalyzeRequest{Code: code}
	var result CryptoAnalyzeResponse
	local := localCryptoAnalysis(code)

	err := c.doRequest("/api/crypto/analyze", reqBody, &result)
	if err != nil {
		if local.Success {
			return local, nil
		}
		return nil, err
	}

	mergeCryptoAnalysis(&result, local)
	return &result, nil
}

func localCryptoAnalysis(code string) *CryptoAnalyzeResponse {
	lowered := strings.ToLower(code)
	containsAny := func(markers []string) int {
		total := 0
		for _, marker := range markers {
			if strings.Contains(lowered, marker) {
				total++
			}
		}
		return total
	}

	libraries := map[string][]string{
		"CryptoJS":   {"cryptojs."},
		"NodeCrypto": {"require('crypto')", "require(\"crypto\")", "createcipheriv", "createhmac", "createhash"},
		"WebCrypto":  {"crypto.subtle", "subtle.encrypt", "subtle.decrypt", "subtle.digest", "subtle.sign"},
		"Forge":      {"forge.", "node-forge"},
		"SJCL":       {"sjcl."},
		"sm-crypto":  {"sm2", "sm3", "sm4", "sm-crypto"},
		"JSEncrypt":  {"jsencrypt", "node-rsa"},
		"jsrsasign":  {"jsrsasign", "rsasign"},
		"tweetnacl":  {"tweetnacl", "nacl.sign", "nacl.box"},
		"elliptic":   {"secp256k1", "elliptic.ec", "ecdh", "ecdsa"},
		"sodium":     {"libsodium", "sodium.", "xchacha20", "ed25519", "x25519"},
	}
	operations := map[string][]string{
		"encrypt": {"encrypt(", "subtle.encrypt", "createcipheriv", ".encrypt("},
		"decrypt": {"decrypt(", "subtle.decrypt", "createdecipheriv", ".decrypt("},
		"sign":    {"sign(", "subtle.sign", "jsonwebtoken.sign", "jws.sign"},
		"verify":  {"verify(", "subtle.verify", "jsonwebtoken.verify", "jws.verify"},
		"hash":    {"createhash", "subtle.digest", "md5(", "sha1(", "sha256(", "sha512(", "sha3", "ripemd160"},
		"kdf":     {"pbkdf2", "scrypt", "bcrypt", "hkdf"},
		"encode":  {"btoa(", "atob(", "base64", "base64url", "jwt"},
	}
	modeMarkers := map[string][]string{
		"CBC": {"cbc"},
		"GCM": {"gcm"},
		"CTR": {"ctr"},
		"ECB": {"ecb"},
		"CFB": {"cfb"},
		"OFB": {"ofb"},
		"CCM": {"ccm"},
		"XTS": {"xts"},
	}
	dynamicSourceMarkers := map[string][]string{
		"storage":      {"localstorage", "sessionstorage", "indexeddb"},
		"cookie":       {"document.cookie"},
		"navigator":    {"navigator."},
		"time":         {"date.now", "new date(", "performance.now"},
		"random":       {"math.random", "getrandomvalues", "randombytes"},
		"env":          {"process.env", "import.meta.env"},
		"window_state": {"window.__", "globalthis.", "window["},
		"network":      {"fetch(", "axios.", "xmlhttprequest", ".response", "await fetch"},
	}
	runtimeSelectorMarkers := map[string][]string{
		"algorithm_variable": {"algorithm", "algo", "ciphername"},
		"mode_variable":      {"mode =", "mode:", "ciphermode"},
		"switch_dispatch":    {"switch(", "case 'aes", "case \"aes"},
		"computed_lookup":    {"[algo]", "[algorithm]", "algorithms[", "ciphers["},
	}
	obfuscationLoaderMarkers := map[string][]string{
		"eval_packer":          {"eval(function(p,a,c,k,e,d)"},
		"hex_array":            {"_0x", "\\x"},
		"base64_loader":        {"atob(", "buffer.from(", "base64"},
		"function_constructor": {"function(", "constructor(\"return this\")", "constructor('return this')"},
		"webpack_loader":       {"__webpack_require__", "webpackjsonp", "webpackchunk"},
		"anti_debug":           {"debugger", "devtools", "setinterval(function(){debugger"},
	}
	sinkCatalog := map[string][]string{
		"CryptoJS.AES.encrypt":       {"cryptojs.aes.encrypt"},
		"CryptoJS.AES.decrypt":       {"cryptojs.aes.decrypt"},
		"CryptoJS.DES.encrypt":       {"cryptojs.des.encrypt"},
		"CryptoJS.TripleDES.encrypt": {"cryptojs.tripledes.encrypt"},
		"CryptoJS.HmacSHA256":        {"cryptojs.hmacsha256", "hmacsha256("},
		"CryptoJS.PBKDF2":            {"cryptojs.pbkdf2", "pbkdf2("},
		"crypto.createCipheriv":      {"createcipheriv"},
		"crypto.createDecipheriv":    {"createdecipheriv"},
		"crypto.createHmac":          {"createhmac"},
		"crypto.createHash":          {"createhash"},
		"crypto.subtle.encrypt":      {"subtle.encrypt"},
		"crypto.subtle.decrypt":      {"subtle.decrypt"},
		"crypto.subtle.sign":         {"subtle.sign"},
		"crypto.subtle.digest":       {"subtle.digest"},
		"sm4.encrypt":                {"sm4.encrypt"},
		"sm2.doSignature":            {"sm2.dosignature"},
		"jwt.sign":                   {"jsonwebtoken.sign", "jwt.sign"},
		"jwt.verify":                 {"jsonwebtoken.verify", "jwt.verify"},
	}
	algorithms := []struct {
		Name    string
		Markers []string
	}{
		{"AES", []string{"cryptojs.aes", "aes-gcm", "aes-cbc", "aes-ctr", "aes-ecb", "createcipheriv", "createdecipheriv", "subtle.encrypt", "subtle.decrypt"}},
		{"DES", []string{"cryptojs.des", "des-cbc", "des-ecb"}},
		{"TripleDES", []string{"cryptojs.tripledes", "des-ede3", "3des", "tripledes"}},
		{"RSA", []string{"jsencrypt", "node-rsa", "publicencrypt", "privatedecrypt", "rsa-oaep", "rsa-pss", "rsasign"}},
		{"ECDSA", []string{"ecdsa", "secp256k1", "elliptic.ec"}},
		{"Ed25519", []string{"ed25519"}},
		{"X25519", []string{"x25519"}},
		{"SM2", []string{"sm2"}},
		{"SM3", []string{"sm3"}},
		{"SM4", []string{"sm4"}},
		{"RC4", []string{"cryptojs.rc4", "rc4"}},
		{"Rabbit", []string{"cryptojs.rabbit", "rabbit"}},
		{"ChaCha20", []string{"chacha20", "xchacha20"}},
		{"Salsa20", []string{"salsa20"}},
		{"Blowfish", []string{"blowfish"}},
		{"Twofish", []string{"twofish"}},
		{"TEA", []string{"tea.encrypt", "tea.decrypt"}},
		{"XTEA", []string{"xtea"}},
		{"XXTEA", []string{"xxtea"}},
		{"HMAC-SHA1", []string{"hmacsha1", "createhmac('sha1", "createhmac(\"sha1"}},
		{"HMAC-SHA256", []string{"hmacsha256", "createhmac('sha256", "createhmac(\"sha256"}},
		{"HMAC-SHA512", []string{"hmacsha512", "createhmac('sha512", "createhmac(\"sha512"}},
		{"MD5", []string{"cryptojs.md5", "md5("}},
		{"SHA1", []string{"cryptojs.sha1", "sha1("}},
		{"SHA256", []string{"cryptojs.sha256", "sha256("}},
		{"SHA512", []string{"cryptojs.sha512", "sha512("}},
		{"SHA3", []string{"cryptojs.sha3", "sha3"}},
		{"RIPEMD160", []string{"ripemd160"}},
		{"PBKDF2", []string{"cryptojs.pbkdf2", "pbkdf2"}},
		{"scrypt", []string{"scrypt"}},
		{"bcrypt", []string{"bcrypt"}},
		{"HKDF", []string{"hkdf"}},
		{"Base64", []string{"btoa(", "atob(", "base64"}},
		{"JWT", []string{"jsonwebtoken.sign", "jsonwebtoken.verify", "jwt.sign", "jwt.verify", "jws.sign"}},
	}

	response := &CryptoAnalyzeResponse{
		Success:     false,
		CryptoTypes: []CryptoType{},
		Keys:        extractCryptoLiterals(code, "(?i)(?:const|let|var)?\\s*(?:appSecret|secret|privateKey|publicKey|aesKey|desKey|rsaKey|signKey|hmacKey|key)\\w*\\s*[:=]\\s*['\"`]([^'\"`\\r\\n]{4,128})['\"`]"),
		Ivs:         extractCryptoLiterals(code, "(?i)(?:const|let|var)?\\s*(?:iv|nonce|salt)\\w*\\s*[:=]\\s*['\"`]([^'\"`\\r\\n]{4,128})['\"`]"),
	}

	for _, alg := range algorithms {
		hits := containsAny(alg.Markers)
		if hits == 0 {
			continue
		}
		modes := make([]string, 0, 4)
		for mode, markers := range modeMarkers {
			if containsAny(markers) > 0 {
				modes = append(modes, mode)
			}
		}
		sort.Strings(modes)
		confidence := 0.55 + 0.12*float64(minInt(hits, 3)) + 0.03*float64(minInt(len(modes), 3))
		if confidence > 0.99 {
			confidence = 0.99
		}
		response.CryptoTypes = append(response.CryptoTypes, CryptoType{
			Name:       alg.Name,
			Confidence: confidence,
			Modes:      modes,
		})
	}
	response.Analysis.AlgorithmAliases = map[string][]string{}
	for _, alg := range algorithms {
		aliases := make([]string, 0, len(alg.Markers))
		for _, marker := range alg.Markers {
			if strings.Contains(lowered, marker) {
				aliases = append(aliases, marker)
			}
		}
		if len(aliases) > 0 {
			response.Analysis.AlgorithmAliases[alg.Name] = uniqueStrings(aliases)
		}
	}
	for name, markers := range sinkCatalog {
		if containsAny(markers) > 0 {
			response.Analysis.CryptoSinks = append(response.Analysis.CryptoSinks, name)
		}
	}
	assignmentRegex := regexp.MustCompile(`(?i)(?:const|let|var)?\s*([A-Za-z_$][\w$]*(?:key|iv|nonce|salt|secret|token)[A-Za-z0-9_$]*)\s*[:=]\s*([^;\n]+)`)
	sourceDetailTokens := map[string][]string{
		"storage.localStorage":   {"localstorage"},
		"storage.sessionStorage": {"sessionstorage"},
		"storage.indexedDB":      {"indexeddb"},
		"cookie.document":        {"document.cookie"},
		"navigator":              {"navigator."},
		"time.date":              {"date.now", "new date("},
		"time.performance":       {"performance.now"},
		"random.math":            {"math.random"},
		"random.crypto":          {"getrandomvalues", "randombytes"},
		"env.process":            {"process.env"},
		"env.import_meta":        {"import.meta.env"},
		"window.bootstrap":       {"window.__", "globalthis.", "window["},
		"network.fetch":          {"fetch(", "await fetch"},
		"network.xhr":            {"xmlhttprequest", ".response"},
		"network.axios":          {"axios."},
		"dom.querySelector":      {"queryselector(", "queryselectorall("},
		"dom.getElementById":     {"getelementbyid("},
		"url.searchParams":       {"urlsearchparams", "searchparams.get("},
	}
	for _, match := range assignmentRegex.FindAllStringSubmatch(code, -1) {
		if len(match) < 3 {
			continue
		}
		variable := strings.TrimSpace(match[1])
		expression := strings.TrimSpace(match[2])
		expressionLower := strings.ToLower(expression)
		sources := make([]string, 0, 2)
		for source, tokens := range sourceDetailTokens {
			for _, token := range tokens {
				if strings.Contains(expressionLower, token) {
					sources = append(sources, source)
					break
				}
			}
		}
		if len(sources) == 0 {
			continue
		}
		response.Analysis.KeyFlowCandidates = append(response.Analysis.KeyFlowCandidates, map[string]interface{}{
			"variable":   variable,
			"expression": trimExpression(expression, 160),
			"sources":    uniqueStrings(sources),
			"dynamic":    true,
		})
	}
	derivationTokens := map[string][]string{
		"hash":   {"sha", "md5(", "ripemd", "digest("},
		"hmac":   {"hmac"},
		"kdf":    {"pbkdf2", "scrypt", "bcrypt", "hkdf"},
		"encode": {"btoa(", "atob(", "base64", "buffer.from", "tostring("},
		"concat": {"concat(", "+", "join("},
		"json":   {"json.stringify", "json.parse"},
		"url":    {"encodeuricomponent", "decodeuricomponent", "urlsearchparams"},
	}
	codeLines := strings.Split(code, "\n")
	for _, candidate := range response.Analysis.KeyFlowCandidates {
		variable := fmt.Sprint(candidate["variable"])
		if variable == "" {
			continue
		}
		trackedVars := []string{variable}
		derivations := make([]map[string]interface{}, 0, 2)
		for _, match := range assignmentRegex.FindAllStringSubmatch(code, -1) {
			if len(match) < 3 {
				continue
			}
			targetVar := strings.TrimSpace(match[1])
			expression := strings.TrimSpace(match[2])
			if hasAnyString(trackedVars, []string{targetVar}) {
				continue
			}
			referencesTracked := false
			for _, tracked := range trackedVars {
				if tracked == "" {
					continue
				}
				if regexp.MustCompile(`\b`+regexp.QuoteMeta(tracked)+`\b`).FindStringIndex(expression) != nil {
					referencesTracked = true
					break
				}
			}
			if !referencesTracked {
				continue
			}
			expressionLower := strings.ToLower(expression)
			kind := "propagate"
			for name, tokens := range derivationTokens {
				for _, token := range tokens {
					if strings.Contains(expressionLower, token) {
						kind = name
						break
					}
				}
				if kind != "propagate" {
					break
				}
			}
			derivations = append(derivations, map[string]interface{}{
				"variable":   targetVar,
				"kind":       kind,
				"expression": trimExpression(expression, 160),
			})
			trackedVars = append(trackedVars, targetVar)
		}
		sinks := make([]string, 0, 2)
		for sinkName, markers := range sinkCatalog {
			matched := false
			for _, line := range codeLines {
				lineLower := strings.ToLower(line)
				if !containsAnyLine(lineLower, markers) {
					continue
				}
				for _, tracked := range trackedVars {
					if tracked == "" {
						continue
					}
					if regexp.MustCompile(`\b`+regexp.QuoteMeta(tracked)+`\b`).FindStringIndex(line) != nil {
						matched = true
						break
					}
				}
				if matched {
					break
				}
			}
			if matched {
				sinks = append(sinks, sinkName)
			}
		}
		if len(derivations) == 0 && len(sinks) == 0 {
			continue
		}
		sourceKinds, _ := candidate["sources"].([]string)
		confidence := 0.55
		if len(sinks) > 0 {
			confidence += 0.10
		}
		confidence += minFloat(0.18, float64(len(derivations))*0.06)
		if len(sourceKinds) > 0 {
			confidence += 0.06
		}
		if confidence > 0.99 {
			confidence = 0.99
		}
		response.Analysis.KeyFlowChains = append(response.Analysis.KeyFlowChains, map[string]interface{}{
			"variable": variable,
			"source": map[string]interface{}{
				"kind":       firstString(sourceKinds, "unknown"),
				"expression": fmt.Sprint(candidate["expression"]),
			},
			"derivations": derivations,
			"sinks":       uniqueStrings(sinks),
			"confidence":  confidence,
		})
	}

	response.Analysis.HasKeyDerivation = containsAny(operations["kdf"]) > 0
	response.Analysis.HasRandomIV = strings.Contains(lowered, "wordarray.random") ||
		strings.Contains(lowered, "randombytes") ||
		strings.Contains(lowered, "getrandomvalues") ||
		strings.Contains(lowered, "nonce") ||
		strings.Contains(lowered, "iv")
	for name, markers := range libraries {
		if containsAny(markers) > 0 {
			response.Analysis.DetectedLibraries = append(response.Analysis.DetectedLibraries, name)
		}
	}
	for name, markers := range operations {
		if containsAny(markers) > 0 {
			response.Analysis.DetectedOperations = append(response.Analysis.DetectedOperations, name)
		}
	}
	for name, markers := range modeMarkers {
		if containsAny(markers) > 0 {
			response.Analysis.DetectedModes = append(response.Analysis.DetectedModes, name)
		}
	}
	for name, markers := range dynamicSourceMarkers {
		if containsAny(markers) > 0 {
			response.Analysis.DynamicKeySources = append(response.Analysis.DynamicKeySources, name)
		}
	}
	for name, markers := range runtimeSelectorMarkers {
		if containsAny(markers) > 0 {
			response.Analysis.RuntimeAlgorithmSelection = append(response.Analysis.RuntimeAlgorithmSelection, name)
		}
	}
	for name, markers := range obfuscationLoaderMarkers {
		if containsAny(markers) > 0 {
			response.Analysis.ObfuscationLoaders = append(response.Analysis.ObfuscationLoaders, name)
		}
	}
	sort.Strings(response.Analysis.DetectedLibraries)
	sort.Strings(response.Analysis.DetectedOperations)
	sort.Strings(response.Analysis.DetectedModes)
	sort.Strings(response.Analysis.CryptoSinks)
	sort.Strings(response.Analysis.DynamicKeySources)
	sort.Strings(response.Analysis.RuntimeAlgorithmSelection)
	sort.Strings(response.Analysis.ObfuscationLoaders)
	for _, item := range response.CryptoTypes {
		response.Analysis.NormalizedAlgorithms = append(response.Analysis.NormalizedAlgorithms, item.Name)
	}
	sort.Strings(response.Analysis.NormalizedAlgorithms)
	response.Analysis.RiskScore = minInt(
		100,
		map[bool]int{true: 18, false: 0}[len(response.Analysis.NormalizedAlgorithms) > 0]+
			minInt(20, len(response.Analysis.DynamicKeySources)*8)+
			minInt(18, len(response.Analysis.RuntimeAlgorithmSelection)*6)+
			minInt(24, len(response.Analysis.ObfuscationLoaders)*8)+
			minInt(16, len(response.Analysis.KeyFlowCandidates)*4)+
			minInt(12, len(response.Analysis.CryptoSinks)*2)+
			map[bool]int{true: 8, false: 0}[hasAnyString(response.Analysis.NormalizedAlgorithms, []string{"RSA", "ECDSA", "Ed25519", "X25519", "SM2"})]+
			map[bool]int{true: 6, false: 0}[hasAnyString(response.Analysis.DetectedLibraries, []string{"WebCrypto", "NodeCrypto", "sodium"})]+
			map[bool]int{true: 6, false: 0}[hasAnyString(response.Analysis.NormalizedAlgorithms, []string{"PBKDF2", "scrypt", "bcrypt", "HKDF"})],
	)
	response.Analysis.ReverseComplexity = complexityLabel(response.Analysis.RiskScore)
	if len(response.Analysis.ObfuscationLoaders) > 0 {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "unpack-loader-first")
	}
	if len(response.Analysis.DynamicKeySources) > 0 {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "trace-key-materialization")
	}
	if len(response.Analysis.RuntimeAlgorithmSelection) > 0 {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "trace-algorithm-branch")
	}
	if hasAnyString(response.Analysis.DetectedLibraries, []string{"WebCrypto"}) {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "hook-webcrypto")
	}
	if hasAnyString(response.Analysis.NormalizedAlgorithms, []string{"JWT", "HMAC-SHA1", "HMAC-SHA256", "HMAC-SHA512"}) {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "rebuild-signing-canonicalization")
	}
	if hasAnyString(response.Analysis.NormalizedAlgorithms, []string{"RSA", "ECDSA", "Ed25519", "X25519", "SM2"}) {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "capture-key-import-and-padding")
	}
	if len(response.Analysis.RecommendedApproach) == 0 {
		response.Analysis.RecommendedApproach = append(response.Analysis.RecommendedApproach, "static-analysis-sufficient")
	}
	response.Analysis.RequiresASTDataflow = len(response.Analysis.DynamicKeySources) > 0 || len(response.Analysis.RuntimeAlgorithmSelection) > 0 || len(response.Analysis.ObfuscationLoaders) > 0 || len(response.Analysis.KeyFlowCandidates) > 0
	response.Analysis.RequiresRuntimeExecution = len(response.Analysis.DynamicKeySources) > 0 || len(response.Analysis.ObfuscationLoaders) > 0 || hasAnyString(response.Analysis.DetectedLibraries, []string{"WebCrypto"}) || len(response.Analysis.CryptoSinks) > 0
	response.Analysis.RequiresLoaderUnpack = len(response.Analysis.ObfuscationLoaders) > 0
	response.Success = len(response.CryptoTypes) > 0
	return response
}

func mergeCryptoAnalysis(remote *CryptoAnalyzeResponse, local *CryptoAnalyzeResponse) {
	if remote == nil || local == nil {
		return
	}
	index := map[string]int{}
	for i, item := range remote.CryptoTypes {
		index[item.Name] = i
	}
	for _, item := range local.CryptoTypes {
		if pos, ok := index[item.Name]; ok {
			if item.Confidence > remote.CryptoTypes[pos].Confidence {
				remote.CryptoTypes[pos].Confidence = item.Confidence
			}
			remote.CryptoTypes[pos].Modes = uniqueStrings(append(remote.CryptoTypes[pos].Modes, item.Modes...))
			continue
		}
		remote.CryptoTypes = append(remote.CryptoTypes, item)
		index[item.Name] = len(remote.CryptoTypes) - 1
	}
	sort.Slice(remote.CryptoTypes, func(i, j int) bool {
		if remote.CryptoTypes[i].Confidence == remote.CryptoTypes[j].Confidence {
			return remote.CryptoTypes[i].Name < remote.CryptoTypes[j].Name
		}
		return remote.CryptoTypes[i].Confidence > remote.CryptoTypes[j].Confidence
	})
	remote.Keys = uniqueStrings(append(remote.Keys, local.Keys...))
	remote.Ivs = uniqueStrings(append(remote.Ivs, local.Ivs...))
	remote.Analysis.HasKeyDerivation = remote.Analysis.HasKeyDerivation || local.Analysis.HasKeyDerivation
	remote.Analysis.HasRandomIV = remote.Analysis.HasRandomIV || local.Analysis.HasRandomIV
	remote.Analysis.DetectedLibraries = uniqueStrings(append(remote.Analysis.DetectedLibraries, local.Analysis.DetectedLibraries...))
	remote.Analysis.DetectedOperations = uniqueStrings(append(remote.Analysis.DetectedOperations, local.Analysis.DetectedOperations...))
	remote.Analysis.DetectedModes = uniqueStrings(append(remote.Analysis.DetectedModes, local.Analysis.DetectedModes...))
	remote.Analysis.NormalizedAlgorithms = uniqueStrings(append(remote.Analysis.NormalizedAlgorithms, local.Analysis.NormalizedAlgorithms...))
	if remote.Analysis.AlgorithmAliases == nil {
		remote.Analysis.AlgorithmAliases = map[string][]string{}
	}
	for name, aliases := range local.Analysis.AlgorithmAliases {
		remote.Analysis.AlgorithmAliases[name] = uniqueStrings(append(remote.Analysis.AlgorithmAliases[name], aliases...))
	}
	remote.Analysis.DynamicKeySources = uniqueStrings(append(remote.Analysis.DynamicKeySources, local.Analysis.DynamicKeySources...))
	remote.Analysis.CryptoSinks = uniqueStrings(append(remote.Analysis.CryptoSinks, local.Analysis.CryptoSinks...))
	remote.Analysis.RuntimeAlgorithmSelection = uniqueStrings(append(remote.Analysis.RuntimeAlgorithmSelection, local.Analysis.RuntimeAlgorithmSelection...))
	remote.Analysis.ObfuscationLoaders = uniqueStrings(append(remote.Analysis.ObfuscationLoaders, local.Analysis.ObfuscationLoaders...))
	remote.Analysis.RecommendedApproach = uniqueStrings(append(remote.Analysis.RecommendedApproach, local.Analysis.RecommendedApproach...))
	for _, item := range local.Analysis.KeyFlowCandidates {
		if !containsFlowCandidate(remote.Analysis.KeyFlowCandidates, item) {
			remote.Analysis.KeyFlowCandidates = append(remote.Analysis.KeyFlowCandidates, item)
		}
	}
	for _, item := range local.Analysis.KeyFlowChains {
		if !containsFlowChain(remote.Analysis.KeyFlowChains, item) {
			remote.Analysis.KeyFlowChains = append(remote.Analysis.KeyFlowChains, item)
		}
	}
	if local.Analysis.RiskScore > remote.Analysis.RiskScore {
		remote.Analysis.RiskScore = local.Analysis.RiskScore
	}
	remote.Analysis.ReverseComplexity = complexityLabel(remote.Analysis.RiskScore)
	remote.Analysis.RequiresASTDataflow = remote.Analysis.RequiresASTDataflow || local.Analysis.RequiresASTDataflow
	remote.Analysis.RequiresRuntimeExecution = remote.Analysis.RequiresRuntimeExecution || local.Analysis.RequiresRuntimeExecution
	remote.Analysis.RequiresLoaderUnpack = remote.Analysis.RequiresLoaderUnpack || local.Analysis.RequiresLoaderUnpack
	if len(remote.CryptoTypes) > 0 && !remote.Success {
		remote.Success = true
	}
}

func extractCryptoLiterals(code string, pattern string) []string {
	re := regexp.MustCompile(pattern)
	matches := re.FindAllStringSubmatch(code, -1)
	results := make([]string, 0, len(matches))
	seen := map[string]struct{}{}
	for _, match := range matches {
		if len(match) < 2 {
			continue
		}
		value := strings.TrimSpace(match[1])
		if len(value) < 4 || len(value) > 128 {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		results = append(results, value)
		if len(results) >= 8 {
			break
		}
	}
	return results
}

func uniqueStrings(values []string) []string {
	seen := map[string]struct{}{}
	result := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" {
			continue
		}
		if _, ok := seen[value]; ok {
			continue
		}
		seen[value] = struct{}{}
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func hasAnyString(values []string, required []string) bool {
	set := map[string]struct{}{}
	for _, value := range values {
		set[value] = struct{}{}
	}
	for _, item := range required {
		if _, ok := set[item]; ok {
			return true
		}
	}
	return false
}

func complexityLabel(score int) string {
	switch {
	case score >= 80:
		return "extreme"
	case score >= 55:
		return "high"
	case score >= 30:
		return "medium"
	default:
		return "low"
	}
}

func trimExpression(value string, limit int) string {
	value = strings.TrimSpace(value)
	if len(value) <= limit {
		return value
	}
	return value[:limit]
}

func containsFlowCandidate(values []map[string]interface{}, expected map[string]interface{}) bool {
	for _, item := range values {
		if fmt.Sprint(item["variable"]) == fmt.Sprint(expected["variable"]) &&
			fmt.Sprint(item["expression"]) == fmt.Sprint(expected["expression"]) {
			return true
		}
	}
	return false
}

func containsFlowChain(values []map[string]interface{}, expected map[string]interface{}) bool {
	for _, item := range values {
		if fmt.Sprint(item["variable"]) == fmt.Sprint(expected["variable"]) &&
			fmt.Sprint(item["source"]) == fmt.Sprint(expected["source"]) &&
			fmt.Sprint(item["sinks"]) == fmt.Sprint(expected["sinks"]) {
			return true
		}
	}
	return false
}

func containsAnyLine(line string, markers []string) bool {
	for _, marker := range markers {
		if strings.Contains(line, marker) {
			return true
		}
	}
	return false
}

func firstString(values []string, fallback string) string {
	if len(values) == 0 {
		return fallback
	}
	return values[0]
}

func minFloat(a float64, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

// CryptoEncryptRequest 加密请求
type CryptoEncryptRequest struct {
	Algorithm string `json:"algorithm"`
	Data      string `json:"data"`
	Key       string `json:"key"`
	IV        string `json:"iv,omitempty"`
	Mode      string `json:"mode,omitempty"`
}

// CryptoResponse 加密/解密响应
type CryptoResponse struct {
	Success   bool   `json:"success"`
	Encrypted string `json:"encrypted,omitempty"`
	Decrypted string `json:"decrypted,omitempty"`
	Hash      string `json:"hash,omitempty"`
	Error     string `json:"error,omitempty"`
}

// Encrypt 执行加密
func (c *NodeReverseClient) Encrypt(req CryptoEncryptRequest) (*CryptoResponse, error) {
	var result CryptoResponse
	err := c.doRequest("/api/crypto/encrypt", req, &result)
	return &result, err
}

// Decrypt 执行解密
func (c *NodeReverseClient) Decrypt(req CryptoEncryptRequest) (*CryptoResponse, error) {
	var result CryptoResponse
	err := c.doRequest("/api/crypto/decrypt", req, &result)
	return &result, err
}

// ExecuteJSRequest JS 执行请求
type ExecuteJSRequest struct {
	Code    string                 `json:"code"`
	Context map[string]interface{} `json:"context,omitempty"`
	Timeout int                    `json:"timeout,omitempty"`
}

// ExecuteJSResponse JS 执行响应
type ExecuteJSResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Error   string      `json:"error,omitempty"`
}

// ExecuteJS 执行 JavaScript 代码
func (c *NodeReverseClient) ExecuteJS(code string, context map[string]interface{}) (*ExecuteJSResponse, error) {
	req := ExecuteJSRequest{
		Code:    code,
		Context: context,
		Timeout: 5000,
	}

	var result ExecuteJSResponse
	err := c.doRequest("/api/js/execute", req, &result)
	return &result, err
}

// ASTAnalyzeRequest AST 分析请求
type ASTAnalyzeRequest struct {
	Code     string   `json:"code"`
	Analysis []string `json:"analysis,omitempty"`
}

// ASTAnalyzeResponse AST 分析响应
type ASTAnalyzeResponse struct {
	Success bool `json:"success"`
	Results struct {
		Crypto      []map[string]interface{} `json:"crypto"`
		Obfuscation []map[string]interface{} `json:"obfuscation"`
		AntiDebug   []map[string]interface{} `json:"antiDebug"`
		Functions   []map[string]interface{} `json:"functions"`
	} `json:"results"`
}

// AnalyzeAST 分析 AST
func (c *NodeReverseClient) AnalyzeAST(code string, analysisTypes []string) (*ASTAnalyzeResponse, error) {
	req := ASTAnalyzeRequest{
		Code:     code,
		Analysis: analysisTypes,
	}

	var result ASTAnalyzeResponse
	err := c.doRequest("/api/ast/analyze", req, &result)
	return &result, err
}

// AnalyzeWebpack 分析 Webpack bundle
func (c *NodeReverseClient) AnalyzeWebpack(code string) (map[string]interface{}, error) {
	req := map[string]interface{}{"code": code}
	var result map[string]interface{}
	err := c.doRequest("/api/webpack/analyze", req, &result)
	return result, err
}

// BrowserSimulateRequest 浏览器模拟请求
type BrowserSimulateRequest struct {
	Code          string            `json:"code"`
	BrowserConfig map[string]string `json:"browserConfig,omitempty"`
}

// BrowserSimulateResponse 浏览器模拟响应
type BrowserSimulateResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Cookies string      `json:"cookies"`
	Error   string      `json:"error,omitempty"`
}

// SimulateBrowser 模拟浏览器环境
func (c *NodeReverseClient) SimulateBrowser(code string, config map[string]string) (*BrowserSimulateResponse, error) {
	req := BrowserSimulateRequest{
		Code:          code,
		BrowserConfig: config,
	}

	var result BrowserSimulateResponse
	err := c.doRequest("/api/browser/simulate", req, &result)
	return &result, err
}

type CanvasFingerprintResponse struct {
	Success     bool                   `json:"success"`
	Fingerprint map[string]interface{} `json:"fingerprint,omitempty"`
	Hash        string                 `json:"hash,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

func (c *NodeReverseClient) CanvasFingerprint() (*CanvasFingerprintResponse, error) {
	var result CanvasFingerprintResponse
	err := c.doRequest("/api/canvas/fingerprint", map[string]interface{}{}, &result)
	return &result, err
}

// FunctionCallRequest 函数调用请求
type FunctionCallRequest struct {
	FunctionName string        `json:"functionName"`
	Args         []interface{} `json:"args"`
	Code         string        `json:"code"`
}

// FunctionCallResponse 函数调用响应
type FunctionCallResponse struct {
	Success bool        `json:"success"`
	Result  interface{} `json:"result"`
	Error   string      `json:"error,omitempty"`
}

// AntiBotProfileRequest 反爬检测/画像请求
type AntiBotProfileRequest struct {
	HTML       string                 `json:"html,omitempty"`
	JS         string                 `json:"js,omitempty"`
	Headers    map[string]interface{} `json:"headers,omitempty"`
	Cookies    string                 `json:"cookies,omitempty"`
	StatusCode int                    `json:"statusCode,omitempty"`
	URL        string                 `json:"url,omitempty"`
}

// AntiBotProfileResponse 反爬检测/画像响应
type AntiBotProfileResponse struct {
	Success          bool                     `json:"success"`
	Detection        map[string]bool          `json:"detection,omitempty"`
	Vendors          []map[string]interface{} `json:"vendors,omitempty"`
	Challenges       []map[string]interface{} `json:"challenges,omitempty"`
	Signals          []string                 `json:"signals,omitempty"`
	Score            int                      `json:"score,omitempty"`
	Level            string                   `json:"level,omitempty"`
	Recommendations  []string                 `json:"recommendations,omitempty"`
	RequestBlueprint map[string]interface{}   `json:"requestBlueprint,omitempty"`
	MitigationPlan   map[string]interface{}   `json:"mitigationPlan,omitempty"`
	Error            string                   `json:"error,omitempty"`
}

type FingerprintSpoofRequest struct {
	Browser  string `json:"browser,omitempty"`
	Platform string `json:"platform,omitempty"`
}

type FingerprintSpoofResponse struct {
	Success     bool                   `json:"success"`
	Fingerprint map[string]interface{} `json:"fingerprint,omitempty"`
	Browser     string                 `json:"browser,omitempty"`
	Platform    string                 `json:"platform,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

type TLSFingerprintRequest struct {
	Browser string `json:"browser,omitempty"`
	Version string `json:"version,omitempty"`
}

type TLSFingerprintResponse struct {
	Success     bool                   `json:"success"`
	Fingerprint map[string]interface{} `json:"fingerprint,omitempty"`
	Browser     string                 `json:"browser,omitempty"`
	Version     string                 `json:"version,omitempty"`
	Error       string                 `json:"error,omitempty"`
}

// CallFunction 调用 JavaScript 函数
func (c *NodeReverseClient) CallFunction(functionName string, args []interface{}, code string) (*FunctionCallResponse, error) {
	req := FunctionCallRequest{
		FunctionName: functionName,
		Args:         args,
		Code:         code,
	}

	var result FunctionCallResponse
	err := c.doRequest("/api/function/call", req, &result)
	return &result, err
}

type SignatureReverseResponse struct {
	Success        bool   `json:"success"`
	FunctionName   string `json:"functionName,omitempty"`
	Input          string `json:"input,omitempty"`
	Output         string `json:"output,omitempty"`
	TotalFunctions int    `json:"totalFunctions,omitempty"`
	SuccessCount   int    `json:"successCount,omitempty"`
	Error          string `json:"error,omitempty"`
}

func (c *NodeReverseClient) ReverseSignature(code string, input string, expectedOutput string) (*SignatureReverseResponse, error) {
	req := map[string]interface{}{
		"code":           code,
		"input":          input,
		"expectedOutput": expectedOutput,
	}
	var result SignatureReverseResponse
	err := c.doRequest("/api/signature/reverse", req, &result)
	return &result, err
}

// DetectAntiBot 检测页面中的反爬特征
func (c *NodeReverseClient) DetectAntiBot(req AntiBotProfileRequest) (*AntiBotProfileResponse, error) {
	var result AntiBotProfileResponse
	err := c.doRequest("/api/anti-bot/detect", req, &result)
	return &result, err
}

// ProfileAntiBot 生成完整的反爬画像与规避计划
func (c *NodeReverseClient) ProfileAntiBot(req AntiBotProfileRequest) (*AntiBotProfileResponse, error) {
	var result AntiBotProfileResponse
	err := c.doRequest("/api/anti-bot/profile", req, &result)
	return &result, err
}

func (c *NodeReverseClient) SpoofFingerprint(req FingerprintSpoofRequest) (*FingerprintSpoofResponse, error) {
	var result FingerprintSpoofResponse
	err := c.doRequest("/api/fingerprint/spoof", req, &result)
	return &result, err
}

func (c *NodeReverseClient) GenerateTLSFingerprint(req TLSFingerprintRequest) (*TLSFingerprintResponse, error) {
	var result TLSFingerprintResponse
	err := c.doRequest("/api/tls/fingerprint", req, &result)
	return &result, err
}

// HealthCheck 健康检查
func (c *NodeReverseClient) HealthCheck() (bool, error) {
	resp, err := c.HTTPClient.Get(c.BaseURL + "/health")
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	return resp.StatusCode == 200, nil
}

// doRequest 执行 HTTP 请求
func (c *NodeReverseClient) doRequest(path string, reqBody interface{}, result interface{}) error {
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return fmt.Errorf("JSON 序列化失败: %v", err)
	}

	req, err := http.NewRequest("POST", c.BaseURL+path, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("创建请求失败: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("服务器返回错误状态码: %d", resp.StatusCode)
	}

	if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
		return fmt.Errorf("JSON 解析失败: %v", err)
	}

	return nil
}
