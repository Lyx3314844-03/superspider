package media

import (
	"regexp"
	"strings"

	"gospider/core"
)

var mediaURLPattern = regexp.MustCompile(`https?://[^\s"'<>]+`)

// Pipeline discovers media artifacts from normalized runtime outputs.
type Pipeline struct {
	outputDir string
}

// NewPipeline creates a media pipeline rooted at the given output directory.
func NewPipeline(outputDir string) *Pipeline {
	return &Pipeline{outputDir: outputDir}
}

// Apply appends discovered media artifacts to a normalized job result.
func (p *Pipeline) Apply(result *core.JobResult, spec core.MediaSpec) error {
	if result == nil || !spec.Enabled {
		return nil
	}

	urls := mediaURLPattern.FindAllString(result.Text, -1)
	for _, url := range urls {
		artifactType := classifyMediaURL(url)
		if artifactType == "" {
			continue
		}
		result.MediaRecord = append(result.MediaRecord, core.MediaArtifact{
			Type: artifactType,
			URL:  url,
			Path: p.outputDir,
		})
	}
	return nil
}

func classifyMediaURL(url string) string {
	lower := strings.ToLower(url)
	switch {
	case strings.Contains(lower, ".m3u8"):
		return "hls"
	case strings.Contains(lower, ".mpd"):
		return "dash"
	case strings.Contains(lower, ".mp4"), strings.Contains(lower, ".webm"), strings.Contains(lower, ".mov"):
		return "video"
	case strings.Contains(lower, ".mp3"), strings.Contains(lower, ".wav"), strings.Contains(lower, ".aac"):
		return "audio"
	case strings.Contains(lower, ".jpg"), strings.Contains(lower, ".jpeg"), strings.Contains(lower, ".png"), strings.Contains(lower, ".gif"), strings.Contains(lower, ".webp"):
		return "image"
	default:
		return ""
	}
}
