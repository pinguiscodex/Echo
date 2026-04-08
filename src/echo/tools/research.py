"""Research tools for Echo AI Chatbot - Wikipedia and DuckDuckGo search."""

import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

from echo.tools.base import ToolResult

logger = logging.getLogger(__name__)


# WIKIPEDIA TOOLS
class WikipediaTools:
    """Wikipedia research tools."""

    def __init__(self):
        self._wiki = None
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes

    def _get_wiki(self):
        """Lazy load Wikipedia API."""
        if self._wiki is None:
            try:
                import wikipediaapi

                self._wiki = wikipediaapi.Wikipedia(
                    user_agent="Echo AI Chatbot (echo-chatbot)", language="en"
                )
                logger.info("Wikipedia API initialized")
            except ImportError:
                logger.error("wikipedia-api not installed. Run: pip install wikipedia-api")
                raise
            except Exception as e:
                logger.error("Failed to initialize Wikipedia: %s", e)
                raise
        return self._wiki

    def _get_cached(self, key: str) -> Optional[str]:
        """Get cached result if not expired."""
        if key in self._cache:
            cached_time, cached_data = self._cache[key]
            if (datetime.now().timestamp() - cached_time) < self._cache_timeout:
                return cached_data
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, data: str):
        """Cache result with timestamp."""
        self._cache[key] = (datetime.now().timestamp(), data)

    def wikipedia_search(self, query: str, results: int = 5) -> ToolResult:
        """Search Wikipedia for articles on a topic."""
        try:
            cache_key = f"wiki_search:{query}:{results}"
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(True, content=cached)

            wiki = self._get_wiki()
            page = wiki.page(query)

            if not page.exists():
                return ToolResult(
                    False,
                    error=f"No Wikipedia article found for '{query}'. Try a different search term.",
                )

            result = {
                "title": page.title,
                "summary": page.summary[:500] + "..." if len(page.summary) > 500 else page.summary,
                "url": page.fullurl,
                "language": page.language,
                "categories": list(page.categories.keys())[:10],
            }

            content = json.dumps(result, indent=2)
            self._set_cached(cache_key, content)

            return ToolResult(
                True, content=content, metadata={"title": page.title, "url": page.fullurl}
            )
        except Exception as e:
            return ToolResult(False, error=f"Wikipedia search failed: {e}")

    def wikipedia_summary(self, query: str, sentences: int = 3) -> ToolResult:
        """Get Wikipedia article summary."""
        try:
            cache_key = f"wiki_summary:{query}:{sentences}"
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(True, content=cached)

            wiki = self._get_wiki()
            page = wiki.page(query)

            if not page.exists():
                return ToolResult(False, error=f"No Wikipedia article found for '{query}'")

            full_summary = page.summary
            sentence_list = full_summary.split(". ")
            if len(sentence_list) > sentences:
                summary_text = ". ".join(sentence_list[:sentences]) + "."
            else:
                summary_text = full_summary

            result = {"title": page.title, "summary": summary_text, "url": page.fullurl}

            content = json.dumps(result, indent=2)
            self._set_cached(cache_key, content)

            return ToolResult(True, content=content, metadata={"title": page.title})
        except Exception as e:
            return ToolResult(False, error=f"Wikipedia summary failed: {e}")

    def wikipedia_full_article(self, query: str) -> ToolResult:
        """Get complete Wikipedia article content."""
        try:
            cache_key = f"wiki_full:{query}"
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(True, content=cached)

            wiki = self._get_wiki()
            page = wiki.page(query)

            if not page.exists():
                return ToolResult(False, error=f"No Wikipedia article found for '{query}'")

            result = {
                "title": page.title,
                "summary": page.summary,
                "content": page.text[:5000],
                "url": page.fullurl,
                "sections": list(page.sections.keys())[:20],
            }

            if len(page.text) > 5000:
                result[
                    "content"
                ] += f"\n\n... (article truncated, total length: {len(page.text)} chars)"

            content = json.dumps(result, indent=2)
            self._set_cached(cache_key, content)

            return ToolResult(
                True, content=content, metadata={"title": page.title, "length": len(page.text)}
            )
        except Exception as e:
            return ToolResult(False, error=f"Failed to get full article: {e}")

    def wikipedia_random(self, count: int = 3) -> ToolResult:
        """Get random Wikipedia articles."""
        try:
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "random", "rnlimit": count, "format": "json"},
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()
            articles = data.get("query", {}).get("random", [])

            result = {
                "articles": [
                    {
                        "title": a["title"],
                        "id": a["id"],
                        "url": f"https://en.wikipedia.org/wiki/{a['title'].replace(' ', '_')}",
                    }
                    for a in articles
                ]
            }

            return ToolResult(True, content=json.dumps(result, indent=2))
        except Exception as e:
            return ToolResult(False, error=f"Failed to get random articles: {e}")


# DUCKDUCKGO TOOLS
class DuckDuckGoTools:
    """DuckDuckGo search tools with advanced dorking."""

    def __init__(self):
        self._ddg = None
        self._cache = {}
        self._cache_timeout = 300

    def _get_ddg(self):
        """Lazy load DuckDuckGo search."""
        if self._ddg is None:
            try:
                from ddgs import DDGS

                self._ddg = DDGS()
                logger.info("DuckDuckGo search initialized")
            except ImportError:
                logger.error("ddgs not installed. Run: pip install ddgs")
                raise
            except Exception as e:
                logger.error("Failed to initialize DuckDuckGo: %s", e)
                raise
        return self._ddg

    def _search_with_retry(self, search_func, query, max_results=10, max_retries=3, **kwargs):
        """Execute search with retry logic and rate limit handling."""
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(1, 3) * attempt
                    logger.info(
                        "Retry %d/%d, waiting %.1f seconds", attempt + 1, max_retries, delay
                    )
                    time.sleep(delay)

                results = list(search_func(query, max_results=max_results, **kwargs))
                return results

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if "403" in error_str or "rate" in error_str:
                    logger.warning("Rate limit hit on attempt %d/%d", attempt + 1, max_retries)
                    if attempt < max_retries - 1:
                        continue
                else:
                    logger.warning("Search error on attempt %d/%d: %s", attempt + 1, max_retries, e)
                    if attempt < max_retries - 1:
                        continue

        raise last_error

    def _get_cached(self, key: str) -> Optional[str]:
        """Get cached result if not expired."""
        if key in self._cache:
            cached_time, cached_data = self._cache[key]
            if (datetime.now().timestamp() - cached_time) < self._cache_timeout:
                return cached_data
            else:
                del self._cache[key]
        return None

    def _set_cached(self, key: str, data: str):
        """Cache result with timestamp."""
        self._cache[key] = (datetime.now().timestamp(), data)

    def web_search(self, query: str, max_results: int = 10, region: str = "wt-wt") -> ToolResult:
        """General web search using DuckDuckGo."""
        try:
            cache_key = f"ddg_web:{query}:{max_results}:{region}"
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(True, content=cached)

            ddg = self._get_ddg()
            results = self._search_with_retry(
                ddg.text, query, max_results=max_results, region=region
            )

            if not results:
                return ToolResult(False, error=f"No web results found for '{query}'")

            formatted = self._format_search_results(results, query)
            content = json.dumps(formatted, indent=2)
            self._set_cached(cache_key, content)

            return ToolResult(
                True, content=content, metadata={"query": query, "count": len(results)}
            )
        except Exception as e:
            return ToolResult(False, error=f"Web search failed: {e}")

    def news_search(self, query: str, max_results: int = 10, region: str = "wt-wt") -> ToolResult:
        """Search for news articles."""
        try:
            cache_key = f"ddg_news:{query}:{max_results}:{region}"
            cached = self._get_cached(cache_key)
            if cached:
                return ToolResult(True, content=cached)

            ddg = self._get_ddg()
            results = self._search_with_retry(
                ddg.news, query, max_results=max_results, region=region
            )

            if not results:
                return ToolResult(False, error=f"No news results found for '{query}'")

            formatted = self._format_news_results(results)
            content = json.dumps(formatted, indent=2)
            self._set_cached(cache_key, content)

            return ToolResult(
                True, content=content, metadata={"query": query, "count": len(results)}
            )
        except Exception as e:
            return ToolResult(False, error=f"News search failed: {e}")

    def dork_search(self, dork_query: str, max_results: int = 10) -> ToolResult:
        """Advanced search with dorking techniques."""
        return self.web_search(dork_query, max_results=max_results)

    def academic_search(self, query: str, max_results: int = 10) -> ToolResult:
        """Search for academic/scholarly results."""
        academic_query = f"{query} site:edu OR site:scholar.google.com OR site:arxiv.org"
        return self.web_search(academic_query, max_results=max_results)

    def code_search(self, query: str, max_results: int = 10) -> ToolResult:
        """Search for code repositories."""
        code_query = f"{query} site:github.com OR site:gitlab.com OR site:bitbucket.org OR site:stackoverflow.com"
        return self.web_search(code_query, max_results=max_results)

    def _format_search_results(self, results: List[Dict], query: str) -> Dict:
        """Format web search results."""
        formatted = {"query": query, "results": []}

        for i, result in enumerate(results[:10], 1):
            formatted["results"].append(
                {
                    "number": i,
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "snippet": result.get("body", "")[:300],
                }
            )

        return formatted

    def _format_news_results(self, results: List[Dict]) -> Dict:
        """Format news search results."""
        formatted = {"results": []}

        for i, result in enumerate(results[:10], 1):
            formatted["results"].append(
                {
                    "number": i,
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "source": result.get("source", ""),
                    "date": result.get("date", ""),
                    "snippet": result.get("body", "")[:300],
                }
            )

        return formatted


# RESEARCH ORCHESTRATOR
class ResearchOrchestrator:
    """Orchestrate multi-source research queries."""

    def __init__(self):
        self.wiki = WikipediaTools()
        self.ddg = DuckDuckGoTools()

    def smart_research(self, query: str, search_types: List[str] = None) -> ToolResult:
        """Auto-select best search methods for a query."""
        if search_types is None:
            search_types = ["web", "wiki"]

        results = []

        for search_type in search_types:
            if search_type == "web":
                result = self.ddg.web_search(query, max_results=5)
                results.append({"type": "web", "result": result})
            elif search_type == "wiki":
                result = self.wiki.wikipedia_summary(query, sentences=3)
                results.append({"type": "wiki", "result": result})
            elif search_type == "news":
                result = self.ddg.news_search(query, max_results=5)
                results.append({"type": "news", "result": result})
            elif search_type == "academic":
                result = self.ddg.academic_search(query, max_results=5)
                results.append({"type": "academic", "result": result})
            elif search_type == "code":
                result = self.ddg.code_search(query, max_results=5)
                results.append({"type": "code", "result": result})

        successful = [r for r in results if r["result"].success]

        if not successful:
            return ToolResult(False, error="No results found from any source")

        combined = {"query": query, "sources_used": [r["type"] for r in successful], "results": {}}

        for r in successful:
            combined["results"][r["type"]] = r["result"].content[:1000]

        return ToolResult(
            True,
            content=json.dumps(combined, indent=2),
            metadata={"query": query, "successful_sources": len(successful)},
        )

    def fact_check(self, query: str) -> ToolResult:
        """Cross-reference multiple sources for fact-checking."""
        results = []

        wiki_result = self.wiki.wikipedia_summary(query, sentences=5)
        if wiki_result.success:
            results.append({"source": "Wikipedia", "result": wiki_result.content[:500]})

        web_result = self.ddg.web_search(query, max_results=5)
        if web_result.success:
            results.append({"source": "Web", "result": web_result.content[:500]})

        news_result = self.ddg.news_search(query, max_results=5)
        if news_result.success:
            results.append({"source": "News", "result": news_result.content[:500]})

        if not results:
            return ToolResult(False, error="No results found for fact-checking")

        combined = {
            "query": query,
            "sources": results,
            "note": "Compare information across sources to verify accuracy",
        }

        return ToolResult(True, content=json.dumps(combined, indent=2))
