#!/usr/bin/env python
"""
Manual YouTube Cookie Exporter

This script opens a browser window where you can:
1. Log into YouTube if needed
2. The cookies will be automatically exported

Run this script and log into your Google account when prompted.
"""
import os
import sys
import http.cookiejar
from pathlib import Path

# Try to use browser_cookie3 which has better Windows support
try:
    import browser_cookie3
    HAS_BC3 = True
except ImportError:
    HAS_BC3 = False
    print("Installing browser_cookie3...")
    os.system(f"{sys.executable} -m pip install browser_cookie3")
    try:
        import browser_cookie3
        HAS_BC3 = True
    except:
        HAS_BC3 = False

COOKIES_PATH = Path(r"c:\Users\saziz\video-dj-playlist\cache\youtube_cookies.txt")

def export_cookies_bc3():
    """Try to export cookies using browser_cookie3"""
    print("\nTrying to extract cookies from browsers...")
    
    # Try different browsers
    browsers = [
        ('Chrome', browser_cookie3.chrome),
        ('Edge', browser_cookie3.edge),
        ('Firefox', browser_cookie3.firefox),
        ('Brave', browser_cookie3.brave),
    ]
    
    for name, func in browsers:
        try:
            print(f"  Trying {name}...")
            cj = func(domain_name='.youtube.com')
            
            # Convert to Netscape format
            cookies = list(cj)
            if cookies:
                print(f"  Found {len(cookies)} cookies from {name}")
                
                # Save in Netscape format
                with open(COOKIES_PATH, 'w') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This is a generated file! Do not edit.\n\n")
                    for cookie in cookies:
                        secure = "TRUE" if cookie.secure else "FALSE"
                        http_only = "TRUE" if hasattr(cookie, 'has_nonstandard_attr') else "FALSE"
                        expiry = str(int(cookie.expires)) if cookie.expires else "0"
                        f.write(f".youtube.com\tTRUE\t/\t{secure}\t{expiry}\t{cookie.name}\t{cookie.value}\n")
                
                print(f"\n✓ Cookies exported to: {COOKIES_PATH}")
                return True
        except Exception as e:
            print(f"    Failed: {e}")
    
    return False

def manual_instructions():
    """Print manual cookie export instructions"""
    print("\n" + "="*60)
    print("MANUAL COOKIE EXPORT INSTRUCTIONS")
    print("="*60)
    print("""
Since automatic extraction failed, you need to manually export cookies:

1. Install a browser extension:
   - Chrome/Edge: "Get cookies.txt LOCALLY" 
     https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

2. Go to https://www.youtube.com and make sure you're logged in

3. Click the extension icon and click "Export" 

4. Save the file to:
   c:\\Users\\saziz\\video-dj-playlist\\cache\\youtube_cookies.txt

5. Run the AI DJ Studio - it should now work!
""")

if __name__ == "__main__":
    print("YouTube Cookie Exporter for AI DJ Studio")
    print("="*50)
    
    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if HAS_BC3:
        if export_cookies_bc3():
            print("\nYou can now use the AI DJ Studio!")
            sys.exit(0)
    
    manual_instructions()
    sys.exit(1)
