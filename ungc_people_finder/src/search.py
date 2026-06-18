"""Search provider abstraction. Supports mock, bing, serpapi, google."""
import time
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src import cache as cache_module

logger = logging.getLogger("ungc.search")

class SearchResult:
    def __init__(self, title: str, url: str, snippet: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet

    def __repr__(self):
        return f"SearchResult(title={self.title!r}, url={self.url!r})"


class BaseSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        ...


class MockSearchProvider(BaseSearchProvider):
    """Returns zero results. Useful for testing structure without API keys."""
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        logger.info(f"[MOCK] search: {query}")
        return []


class BingSearchProvider(BaseSearchProvider):
    BASE = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        cached = cache_module.get(f"bing:{query}", settings.cache_ttl_hours)
        if cached is not None:
            return [SearchResult(**r) for r in cached]
        time.sleep(settings.search_delay)
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        params = {"q": query, "count": min(num_results, 50), "mkt": "en-AU"}
        with httpx.Client(timeout=15) as client:
            r = client.get(self.BASE, headers=headers, params=params)
            r.raise_for_status()
        items = r.json().get("webPages", {}).get("value", [])
        results = [SearchResult(i["name"], i["url"], i.get("snippet", "")) for i in items]
        cache_module.set(f"bing:{query}", [{"title": x.title, "url": x.url, "snippet": x.snippet} for x in results])
        return results


class SerpApiSearchProvider(BaseSearchProvider):
    BASE = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        cached = cache_module.get(f"serp:{query}", settings.cache_ttl_hours)
        if cached is not None:
            return [SearchResult(**r) for r in cached]
        time.sleep(settings.search_delay)
        params = {"q": query, "num": num_results, "api_key": self.api_key, "engine": "google", "gl": "au"}
        with httpx.Client(timeout=20) as client:
            r = client.get(self.BASE, params=params)
            r.raise_for_status()
        items = r.json().get("organic_results", [])
        results = [SearchResult(i.get("title", ""), i["link"], i.get("snippet", "")) for i in items]
        cache_module.set(f"serp:{query}", [{"title": x.title, "url": x.url, "snippet": x.snippet} for x in results])
        return results


class GoogleCSESearchProvider(BaseSearchProvider):
    BASE = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str, cse_id: str):
        self.api_key = api_key
        self.cse_id = cse_id

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        cached = cache_module.get(f"google:{query}", settings.cache_ttl_hours)
        if cached is not None:
            return [SearchResult(**r) for r in cached]
        time.sleep(settings.search_delay)
        params = {"q": query, "num": min(num_results, 10), "key": self.api_key, "cx": self.cse_id}
        with httpx.Client(timeout=20) as client:
            r = client.get(self.BASE, params=params)
            r.raise_for_status()
        items = r.json().get("items", [])
        results = [SearchResult(i.get("title", ""), i["link"], i.get("snippet", "")) for i in items]
        cache_module.set(f"google:{query}", [{"title": x.title, "url": x.url, "snippet": x.snippet} for x in results])
        return results


def get_provider() -> BaseSearchProvider:
    p = settings.search_provider.lower()
    if p == "bing":
        if not settings.bing_api_key:
            raise ValueError("BING_API_KEY not set")
        return BingSearchProvider(settings.bing_api_key)
    if p == "serpapi":
        if not settings.serpapi_key:
            raise ValueError("SERPAPI_KEY not set")
        return SerpApiSearchProvider(settings.serpapi_key)
    if p == "google":
        if not settings.google_api_key or not settings.google_cse_id:
            raise ValueError("GOOGLE_API_KEY and GOOGLE_CSE_ID must both be set")
        return GoogleCSESearchProvider(settings.google_api_key, settings.google_cse_id)
    return MockSearchProvider()
