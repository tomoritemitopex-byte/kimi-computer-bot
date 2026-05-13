import httpx
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


async def web_fetch(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(headers=BROWSER_HEADERS, timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else "No title"

        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        text = "\n".join(lines)

        if len(text) > 20000:
            text = text[:20000] + "\n\n[Content truncated...]"

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            link_text = a.get_text(strip=True)
            if link_text and href and not href.startswith(("#", "javascript:", "mailto:")):
                links.append({"text": link_text[:80], "url": href})
                if len(links) >= 30:
                    break

        return {
            "title": title,
            "url": url,
            "content": text,
            "links": links,
            "status_code": response.status_code,
        }
    except httpx.TimeoutException:
        return {"error": f"Timeout fetching {url}", "title": "", "content": "", "links": []}
    except Exception as e:
        return {"error": f"Failed to fetch {url}: {str(e)}", "title": "", "content": "", "links": []}


async def web_search(query: str) -> dict:
    search_url = f"https://html.duckduckgo.com/html/?q={query}"
    result = await web_fetch(search_url)

    if "error" in result:
        return result

    soup = BeautifulSoup(f"<html><body>{result.get('content', '')}</body></html>", "lxml")
    results = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)
        if text and href and "duckduckgo" not in href and not href.startswith("#"):
            results.append({"title": text[:100], "url": href})
            if len(results) >= 10:
                break

    return {
        "query": query,
        "results": results,
        "summary": f"Found {len(results)} results for '{query}'",
    }
