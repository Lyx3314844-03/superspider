package scrapy

import (
	"fmt"
	"sort"
	"strings"
)

type PluginFactory func() Plugin

var pluginRegistry = map[string]PluginFactory{}

func RegisterPlugin(name string, factory PluginFactory) {
	if factory == nil {
		return
	}
	name = strings.TrimSpace(name)
	if name == "" {
		return
	}
	pluginRegistry[name] = factory
}

func RegisteredPluginNames() []string {
	names := make([]string, 0, len(pluginRegistry))
	for name := range pluginRegistry {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func ResolvePlugin(name string) (Plugin, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return nil, fmt.Errorf("plugin name is required")
	}
	factory, ok := pluginRegistry[name]
	if !ok {
		return nil, fmt.Errorf("unknown plugin: %s", name)
	}
	return factory(), nil
}

func (c *CrawlerProcess) AddNamedPlugin(name string) error {
	plugin, err := ResolvePlugin(name)
	if err != nil {
		return err
	}
	c.AddPlugin(plugin)
	return nil
}
