import json
import logging
import re
import requests
import sys

log = logging.getLogger(__name__)

MAX_RESULTS = 10

def _find_products(obj, results=None):
    if results is None:
        results = []
    if isinstance(obj, dict):
        if 'productInfo' in obj and isinstance(obj['productInfo'], dict) and 'value' in obj['productInfo']:
            results.append(obj['productInfo']['value'])
        for k, v in obj.items():
            _find_products(v, results)
    elif isinstance(obj, list):
        for item in obj:
            _find_products(item, results)
    return results

def scrape_flipkart(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    results = []
    log.info("Scraping Flipkart (Production API) for: '%s'", query)
    
    # 1. Fetch raw HTML using requests with a randomized User Agent, with retries
    from fake_useragent import UserAgent
    import requests
    import time
    
    html = ""
    for attempt in range(3):
        try:
            ua = UserAgent(os="windows", browsers=["chrome"]).random
            url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}&otracker=search"
            headers = {
                'User-Agent': ua,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                html = response.text
                break
            else:
                log.warning("Flipkart returned status %s on attempt %d", response.status_code, attempt + 1)
        except Exception as e:
            log.warning("Failed to fetch Flipkart HTML via requests on attempt %d: %s", attempt + 1, e)
            
        if attempt < 2:
            time.sleep(1) # wait a bit before retrying

    if not html:
        log.error("Failed to fetch Flipkart HTML after 3 attempts.")
        return results

    # 2. Extract JSON state
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});', html)
    if not match:
        log.error("Could not find __INITIAL_STATE__ JSON in Flipkart HTML. Layout might have changed or bot protection is active.")
        return results
        
    try:
        state = json.loads(match.group(1))
    except Exception as e:
        log.error("Failed to parse Flipkart JSON state: %s", e)
        return results

    # 3. Parse products
    raw_products = _find_products(state)
    log.info("Found %d raw product objects in Flipkart JSON", len(raw_products))
    
    seen_urls = set()
    for p in raw_products:
        if len(results) >= max_results:
            break
            
        try:
            title = p.get('titles', {}).get('title')
            if not title:
                continue
                
            pricing = p.get('pricing', {})
            price = pricing.get('finalPrice', {}).get('value')
            if price is None and 'prices' in pricing:
                for pr in pricing['prices']:
                    if not pr.get('strikeOff'):
                        price = pr.get('value')
                        break
            if price is None:
                continue
                
            rating = p.get('rating', {}).get('average', "N/A")
            reviews = p.get('rating', {}).get('count', "N/A")
            
            p_url = p.get('smartUrl') or p.get('baseUrl')
            if not p_url:
                continue
                
            if p_url in seen_urls:
                continue
            seen_urls.add(p_url)
            
            image = p.get('media', {}).get('images', [{}])[0].get('url', '')
            if image:
                image = image.replace("{@width}", "400").replace("{@height}", "400").replace("{@quality}", "70")

            results.append({
                "title": str(title),
                "price": f"₹{price}",
                "rating": str(rating),
                "reviews_count": str(reviews),
                "url": p_url if p_url.startswith("http") else f"https://www.flipkart.com{p_url}",
                "image": image or "N/A",
                "source": "flipkart"
            })
            log.debug("  [%d] Flipkart -> %s", len(results), title[:60])
        except Exception as e:
            log.warning("Error parsing a Flipkart product: %s", e)
            continue
            
    log.info("Scrape complete — %d products returned from Flipkart.", len(results))
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    query = " ".join(sys.argv[1:]) or "mechanical keyboard"
    data = scrape_flipkart(query)
    print(json.dumps(data, indent=2))
