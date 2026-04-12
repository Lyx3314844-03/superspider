package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"

	"gospider/core"
)

func curlCommand(args []string) int {
	if len(args) == 0 || args[0] != "convert" {
		fmt.Fprintln(os.Stderr, "usage: gospider curl convert --command <curl> [--target <go|http|resty>]")
		return 2
	}

	cmd := flag.NewFlagSet("curl convert", flag.ContinueOnError)
	cmd.SetOutput(io.Discard)
	curlInput := cmd.String("command", "", "curl 命令字符串")
	target := cmd.String("target", "resty", "输出目标: go|http|resty")
	if err := cmd.Parse(args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, "usage: gospider curl convert --command <curl> [--target <go|http|resty>]")
		return 2
	}

	commandText := strings.TrimSpace(*curlInput)
	if commandText == "" {
		remaining := cmd.Args()
		if len(remaining) > 0 {
			commandText = strings.TrimSpace(strings.Join(remaining, " "))
		}
	}
	if commandText == "" {
		fmt.Fprintln(os.Stderr, "gospider curl convert requires --command")
		return 2
	}

	converter := core.NewCurlToGoConverter()
	resolvedTarget := strings.ToLower(strings.TrimSpace(*target))
	var (
		code string
		err  error
	)
	switch resolvedTarget {
	case "go":
		code, err = converter.Convert(commandText)
		if err != nil {
			resolvedTarget = "resty"
			code = converter.ConvertToResty(commandText)
			err = nil
		}
	case "http", "net/http":
		resolvedTarget = "http"
		code, err = converter.ConvertToHTTP(commandText)
		if err != nil {
			resolvedTarget = "resty"
			code = converter.ConvertToResty(commandText)
			err = nil
		}
	case "resty":
		code = converter.ConvertToResty(commandText)
	default:
		fmt.Fprintf(os.Stderr, "unsupported curl target: %s\n", *target)
		return 2
	}

	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		return 1
	}

	payload := map[string]any{
		"command": "curl convert",
		"runtime": "go",
		"target":  resolvedTarget,
		"curl":    commandText,
		"code":    code,
	}
	encoded, marshalErr := json.MarshalIndent(payload, "", "  ")
	if marshalErr != nil {
		fmt.Fprintln(os.Stderr, marshalErr.Error())
		return 1
	}
	fmt.Println(string(encoded))
	return 0
}
