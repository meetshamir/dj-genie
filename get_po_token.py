#!/usr/bin/env python
"""
Get YouTube PO Token using nodriver browser automation.
This opens a real browser and extracts the proof-of-origin token.
"""
import asyncio
import json
import re
from pathlib import Path

CACHE_DIR = Path(r"c:\Users\saziz\video-dj-playlist\cache")
PO_TOKEN_FILE = CACHE_DIR / "po_token.json"


async def get_po_token():
    """Get PO token by visiting YouTube in a real browser."""
    import nodriver as uc
    
    print("Launching browser...")
    browser = await uc.start()
    
    print("Navigating to YouTube...")
    page = await browser.get("https://www.youtube.com")
    
    # Wait for page to load
    await asyncio.sleep(3)
    
    print("Extracting tokens...")
    
    # Get the VISITOR_INFO1_LIVE cookie
    cookies = await page.browser.cookies.get_all()
    visitor_data = None
    for cookie in cookies:
        if cookie.name == "VISITOR_INFO1_LIVE":
            visitor_data = cookie.value
            break
    
    # Get PO token from ytcfg
    po_token = None
    try:
        result = await page.evaluate("window.ytcfg && window.ytcfg.get('INNERTUBE_CONTEXT').client.visitorData")
        if result:
            visitor_data = result
    except:
        pass
    
    try:
        result = await page.evaluate("window.ytcfg && window.ytcfg.get('PLAYER_CONFIG')")
        if result and "poToken" in str(result):
            # Extract poToken from the config
            match = re.search(r'"poToken"\s*:\s*"([^"]+)"', str(result))
            if match:
                po_token = match.group(1)
    except:
        pass
    
    # Alternative: Get from localStorage or sessionStorage
    if not po_token:
        try:
            result = await page.evaluate("""
                (() => {
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        if (script.textContent.includes('poToken')) {
                            const match = script.textContent.match(/"poToken"\\s*:\\s*"([^"]+)"/);
                            if (match) return match[1];
                        }
                    }
                    return null;
                })()
            """)
            if result:
                po_token = result
        except:
            pass
    
    await browser.stop()
    
    if visitor_data:
        print(f"Visitor Data: {visitor_data[:30]}...")
    if po_token:
        print(f"PO Token: {po_token[:30]}...")
    
    # Save to file
    token_data = {
        "visitor_data": visitor_data,
        "po_token": po_token
    }
    
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(PO_TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"\nTokens saved to: {PO_TOKEN_FILE}")
    return token_data


if __name__ == "__main__":
    print("YouTube PO Token Extractor")
    print("=" * 40)
    result = asyncio.run(get_po_token())
    print("\nResult:", result)
