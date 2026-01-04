#!/usr/bin/env python3
"""
Generate a PEP 503 compliant simple repository index from
GitHub releases of flash-attention-prebuild-wheels.
"""

import json
import re
import os
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

GITHUB_REPO = "mjun0812/flash-attention-prebuild-wheels"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def normalize_name(name: str) -> str:
    """Normalize package name according to PEP 503."""
    return re.sub(r'[-_.]+', '-', name).lower()


def get_all_releases() -> list:
    """Fetch all releases from GitHub API."""
    releases = []
    page = 1
    
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    while True:
        url = f"{API_URL}?page={page}&per_page=100"
        req = Request(url, headers=headers)
        
        try:
            with urlopen(req) as response:
                data = json.loads(response.read().decode())
        except HTTPError as e:
            print(f"Error fetching page {page}: {e}")
            break
            
        if not data:
            break
            
        releases.extend(data)
        print(f"  Fetched page {page} ({len(data)} releases)")
        page += 1
    
    return releases


def extract_wheels(releases: list) -> list:
    """Extract wheel file information from releases."""
    wheels = []
    
    for release in releases:
        tag = release.get("tag_name", "unknown")
        
        for asset in release.get("assets", []):
            filename = asset["name"]
            
            if filename.endswith(".whl"):
                wheels.append({
                    "filename": filename,
                    "url": asset["browser_download_url"],
                    "size": asset.get("size", 0),
                    "tag": tag,
                })
    
    return wheels


def generate_root_index(packages: list) -> str:
    """Generate the root /simple/ index.html."""
    links = "\n".join(
        f'    <a href="{pkg}/">{pkg}</a><br/>'
        for pkg in sorted(packages)
    )
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Simple Index</title>
</head>
<body>
    <h1>Simple Index</h1>
{links}
</body>
</html>"""


def generate_package_index(package_name: str, wheels: list) -> str:
    """Generate the package-specific index.html."""
    # Sort wheels by filename for consistent ordering
    sorted_wheels = sorted(wheels, key=lambda w: w["filename"])
    
    links = "\n".join(
        f'    <a href="{w["url"]}#sha256=" data-dist-info-metadata="false">{w["filename"]}</a><br/>'
        for w in sorted_wheels
    )
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for {package_name}</title>
</head>
<body>
    <h1>Links for {package_name}</h1>
{links}
</body>
</html>"""


def main():
    print("=" * 60)
    print("Flash Attention Wheel Index Generator")
    print("=" * 60)
    
    # Fetch releases
    print("\n[1/4] Fetching releases from GitHub...")
    releases = get_all_releases()
    print(f"      Found {len(releases)} releases total")
    
    # Extract wheels
    print("\n[2/4] Extracting wheel files...")
    wheels = extract_wheels(releases)
    print(f"      Found {len(wheels)} wheel files")
    
    if not wheels:
        print("ERROR: No wheels found!")
        return 1
    
    # Group by normalized package name
    print("\n[3/4] Grouping packages...")
    packages = {}
    for wheel in wheels:
        # Extract package name from wheel filename
        name_part = wheel["filename"].split("-")[0]
        normalized = normalize_name(name_part)
        
        if normalized not in packages:
            packages[normalized] = []
        packages[normalized].append(wheel)
    
    for pkg, pkg_wheels in packages.items():
        print(f"      {pkg}: {len(pkg_wheels)} wheels")
    
    # Generate output
    print("\n[4/4] Generating index files...")
    output_dir = Path("public/simple")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Root index
    root_html = generate_root_index(packages.keys())
    (output_dir / "index.html").write_text(root_html)
    print(f"      Created: {output_dir}/index.html")
    
    # Package indices
    for pkg_name, pkg_wheels in packages.items():
        pkg_dir = output_dir / pkg_name
        pkg_dir.mkdir(exist_ok=True)
        
        pkg_html = generate_package_index(pkg_name, pkg_wheels)
        (pkg_dir / "index.html").write_text(pkg_html)
        print(f"      Created: {pkg_dir}/index.html")
    
    # Create a nice landing page
    landing_html = generate_landing_page(packages, len(wheels))
    (Path("public") / "index.html").write_text(landing_html)
    
    print("\n" + "=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print(f"\nOutput directory: {output_dir.absolute()}")
    print("\nUsage:")
    print("  pip install flash-attn --index-url https://<your-domain>/simple/")
    print("\nOr with PyPI fallback:")
    print("  pip install flash-attn --extra-index-url https://<your-domain>/simple/")
    
    return 0


def generate_landing_page(packages: dict, total_wheels: int) -> str:
    """Generate a nice landing page."""
    pkg_list = "\n".join(
        f"<li><strong>{pkg}</strong>: {len(wheels)} wheels</li>"
        for pkg, wheels in sorted(packages.items())
    )
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Flash Attention Pre-built Wheels Index</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }}
        h1 {{ color: #2d3748; }}
        code {{
            background: #f1f5f9;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        .stats {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
        }}
        a {{ color: #3b82f6; }}
    </style>
</head>
<body>
    <h1>🚀 Flash Attention Pre-built Wheels</h1>
    
    <p>
        This is a PEP 503 compliant Python package index for pre-built 
        <a href="https://github.com/Dao-AILab/flash-attention">Flash Attention</a> wheels,
        sourced from <a href="https://github.com/mjun0812/flash-attention-prebuild-wheels">mjun0812/flash-attention-prebuild-wheels</a>.
    </p>
    
    <div class="stats">
        <strong>📦 {total_wheels}</strong> wheels available for <strong>{len(packages)}</strong> package(s)
    </div>
    
    <h2>Installation</h2>
    
    <p>Install flash-attn using this index:</p>
    <pre><code>pip install flash-attn --index-url https://YOUR_DOMAIN/simple/</code></pre>
    
    <p>Or use as an extra index (with PyPI fallback):</p>
    <pre><code>pip install flash-attn --extra-index-url https://YOUR_DOMAIN/simple/</code></pre>
    
    <p>Install a specific version:</p>
    <pre><code>pip install flash-attn==2.5.9 --index-url https://YOUR_DOMAIN/simple/</code></pre>
    
    <h2>Available Packages</h2>
    <ul>
        {pkg_list}
    </ul>
    
    <p>
        <a href="simple/">Browse the simple index →</a>
    </p>
    
    <hr>
    <p style="color: #64748b; font-size: 0.875rem;">
        Auto-generated from GitHub releases. 
        Wheels are served directly from GitHub.
    </p>
</body>
</html>"""


if __name__ == "__main__":
    exit(main())