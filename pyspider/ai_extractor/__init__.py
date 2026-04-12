"""
AI-powered content extractor for pyspider
Uses OpenAI GPT models for intelligent content extraction
"""

import os
import json
import re
from typing import Dict, List, Any

try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class AIExtractor:
    """
    AI-powered content extraction using large language models
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.provider = self.config.get("provider", "openai")
        self.model = self.config.get("model", "gpt-4")
        self.api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY"))
        self.base_url = self.config.get("base_url", "https://api.openai.com/v1")
        self.max_tokens = self.config.get("max_tokens", 4000)
        self.temperature = self.config.get("temperature", 0.3)
        self.timeout = self.config.get("timeout", 60)

        self._init_client()

    def _init_client(self):
        """Initialize the AI client based on provider"""
        if self.provider == "openai" and HAS_OPENAI:
            openai.api_key = self.api_key
            if self.base_url:
                openai.api_base = self.base_url
            self.client = openai
        elif self.provider == "anthropic" and HAS_ANTHROPIC:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def extract(self, html: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from HTML using AI

        Args:
            html: Raw HTML content
            schema: JSON schema defining what to extract

        Returns:
            Extracted data matching the schema
        """
        if not self.client:
            return {"error": "AI client not initialized"}

        prompt = self._build_extraction_prompt(html, schema)

        try:
            if self.provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert web scraper. Extract structured data from HTML content.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )
                result = response.choices[0].message.content
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = response.content[0].text

            return self._parse_json_response(result)
        except Exception as e:
            return {"error": str(e)}

    def _build_extraction_prompt(self, html: str, schema: Dict[str, Any]) -> str:
        """Build the extraction prompt"""
        schema_str = json.dumps(schema, indent=2)

        # Truncate HTML if too long
        truncated_html = html[:8000] if len(html) > 8000 else html

        return f"""
Extract data from the following HTML content.

Schema (extract fields according to this structure):
{schema_str}

HTML Content:
{truncated_html}

Return ONLY valid JSON matching the schema. No additional text.
"""

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        # Try to extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_response": response}

    def extract_with_xpath_suggestion(
        self, html: str, description: str
    ) -> Dict[str, Any]:
        """
        Analyze HTML and suggest optimal XPath selectors
        """
        if not self.client:
            return {"error": "AI client not initialized"}

        prompt = f"""
Analyze this HTML and suggest the best XPath selectors to extract: {description}

HTML (truncated):
{html[:5000]}

Return JSON with:
- "xpath": suggested XPath
- "css": suggested CSS selector
- "confidence": confidence level (0-1)
- "alternatives": list of alternative selectors
"""

        try:
            if self.provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at web scraping and XPath selectors.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.3,
                )
                result = response.choices[0].message.content

            return self._parse_json_response(result)
        except Exception as e:
            return {"error": str(e)}

    def detect_content_type(self, html: str) -> Dict[str, Any]:
        """
        Detect the type of content on the page
        """
        prompt = f"""
Analyze this HTML and detect what type of content it contains.

Return JSON with:
- "type": content type (article, product, review, profile, listing, forum, social, other)
- "confidence": confidence level (0-1)
- "title_field": likely field for title/content
- "metadata": any detected metadata

HTML:
{html[:5000]}
"""

        try:
            if self.provider == "openai":
                response = self.client.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a web content analyzer.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=500,
                    temperature=0.3,
                )
                result = response.choices[0].message.content

            return self._parse_json_response(result)
        except Exception as e:
            return {"error": str(e)}


class SmartXPather:
    """
    AI-powered XPath generation from examples
    """

    def __init__(self, ai_extractor: AIExtractor = None):
        self.ai = ai_extractor or AIExtractor()

    def generate_xpath(
        self, html: str, examples: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate XPath from examples

        Args:
            html: Sample HTML
            examples: List of {field: value} examples
        """
        prompt = f"""
Given these examples of data to extract from HTML:
{json.dumps(examples, indent=2)}

HTML:
{html[:5000]}

Generate the best XPath and CSS selectors to extract this data.
Return JSON with selectors for each field.
"""

        try:
            response = self.ai.client.ChatCompletion.create(
                model=self.ai.model,
                messages=[
                    {"role": "system", "content": "You are an XPath expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.3,
            )
            result = response.choices[0].message.content
            return self.ai._parse_json_response(result)
        except Exception as e:
            return {"error": str(e)}


# Factory function
def create_extractor(config: Dict[str, Any] = None) -> AIExtractor:
    """Create an AI extractor instance"""
    return AIExtractor(config)
