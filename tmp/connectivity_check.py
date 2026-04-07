import urllib.request
import ssl

def check():
    urls = [
        "https://www.google.com",
        "https://raw.githubusercontent.com/Nikunjxx/snowrunner-save-editor-web/main/public/mr/data.js",
        "https://www.maprunner.info/mr/data.js"
    ]
    
    # Create SSL context to bypass cert issues in this restricted env if needed
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url in urls:
        print(f"Checking {url}...")
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=10) as response:
                print(f"  ✅ SUCCESS: {response.status}")
                # print first 100 bytes
                print(f"  Data snippet: {response.read(100)}")
        except Exception as e:
            print(f"  ❌ FAILED: {str(e)}")

if __name__ == "__main__":
    check()
