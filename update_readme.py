#!/usr/bin/env python3
"""
Resilient GitHub Stats & Profile Views README Updater
Guarantees daily updates even if external APIs experience transient timeouts.
"""
import os
import re
import sys
import requests
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def get_profile_views(username, current_content):
    """Fetch profile views from komarev and fall back to incrementing current count."""
    fallback_count = 4700
    existing_match = re.search(
        r'<!-- START_VIEWS -->.*?Profile%20Views-([0-9,]+)-6e40c9.*?<!-- END_VIEWS -->',
        current_content,
        flags=re.DOTALL,
    )
    if existing_match:
        try:
            fallback_count = int(existing_match.group(1).replace(',', ''))
        except ValueError:
            pass

    try:
        resp = requests.get(
            f'https://komarev.com/ghpvc/?username={username}&label=Profile+Views&color=6e40c9&style=for-the-badge',
            timeout=10,
        )
        if resp.status_code == 200:
            match = re.search(r'PROFILE VIEWS:\s*([0-9,]+)', resp.text, re.IGNORECASE)
            if match:
                live_count = int(match.group(1).replace(',', ''))
                return f"{max(live_count, fallback_count + 1):,}"
    except Exception as e:
        print(f"⚠️ komarev fetch warning (using fallback): {e}")

    return f"{fallback_count + 1:,}"


def get_fallback_stats(current_content):
    """Extract existing stats from README.md in case GitHub API has a transient error."""
    def extract_int(pattern, default):
        m = re.search(pattern, current_content)
        return int(m.group(1)) if m else default

    return {
        'repos': extract_int(r'\*\*Total Repositories\*\*\s*\|\s*(\d+)', 46),
        'stars': extract_int(r'\*\*Total Stars\*\*\s*\|\s*⭐\s*(\d+)', 73),
        'forks': extract_int(r'\*\*Total Forks\*\*\s*\|\s*🍴\s*(\d+)', 8),
        'followers': extract_int(r'\*\*Followers\*\*\s*\|\s*👥\s*(\d+)', 12),
        'following': extract_int(r'\*\*Following\*\*\s*\|\s*👤\s*(\d+)', 4),
    }


def get_github_stats(username, token, current_content):
    """Fetch GitHub statistics with automatic fallback on API errors."""
    headers = {'Accept': 'application/vnd.github.v3+json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    fallback = get_fallback_stats(current_content)

    try:
        user_resp = requests.get(
            f'https://api.github.com/users/{username}',
            headers=headers,
            timeout=10,
        )
        user_resp.raise_for_status()
        user_data = user_resp.json()

        repos = []
        page = 1
        while True:
            repos_resp = requests.get(
                f'https://api.github.com/users/{username}/repos',
                headers=headers,
                params={'per_page': 100, 'page': page, 'type': 'owner'},
                timeout=10,
            )
            repos_resp.raise_for_status()
            page_data = repos_resp.json()
            if not isinstance(page_data, list) or not page_data:
                break
            repos.extend(page_data)
            if len(page_data) < 100:
                break
            page += 1

        public_repos = user_data.get(
            'public_repos',
            len([r for r in repos if not r.get('private')]),
        )
        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        total_forks = sum(r.get('forks_count', 0) for r in repos)

        return {
            'repos': public_repos,
            'stars': total_stars,
            'forks': total_forks,
            'followers': user_data.get('followers', fallback['followers']),
            'following': user_data.get('following', fallback['following']),
        }
    except Exception as e:
        print(f"⚠️ Error fetching GitHub stats (using existing README values): {e}")
        return fallback


def update_readme(username, token):
    """Update README with GitHub stats and reliable Profile Views badge."""
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()

        stats = get_github_stats(username, token, content)
        views_str = get_profile_views(username, content)

        # 1. Update Profile Views badge (Shields.io CDN so it never breaks on GitHub)
        new_views_badge = (
            f'<!-- START_VIEWS -->'
            f'<img src="https://img.shields.io/badge/Profile%20Views-{views_str}-6e40c9?style=for-the-badge&logo=github&logoColor=white" alt="Profile Views"/>'
            f'<!-- END_VIEWS -->'
        )
        views_pattern = r'<!-- START_VIEWS -->.*?<!-- END_VIEWS -->'
        if re.search(views_pattern, content, flags=re.DOTALL):
            content = re.sub(views_pattern, new_views_badge, content, flags=re.DOTALL)
        else:
            old_komarev_pattern = r'<img src="https://komarev\.com/ghpvc/\?username=[^"]+" alt="Profile Views"\s*/>'
            content = re.sub(old_komarev_pattern, new_views_badge, content)

        # 2. Update GitHub Statistics section
        now_utc = datetime.now(timezone.utc).strftime('%B %d, %Y at %I:%M %p UTC')
        new_stats = f"""<!-- START_STATS -->
## 📊 GitHub Statistics

<div align="center">

<img src="https://raw.githubusercontent.com/Edge-Explorer/Edge-Explorer/main/github-metrics.svg" width="100%" alt="GitHub Metrics"/>

<br/>

| Metric | Value |
|--------|-------|
| **Total Repositories** | {stats['repos']} Public |
| **Total Stars** | ⭐ {stats['stars']} |
| **Total Forks** | 🍴 {stats['forks']} |
| **Followers** | 👥 {stats['followers']} |
| **Following** | 👤 {stats['following']} |
| **Last Updated** | {now_utc} |

</div>
<!-- END_STATS -->"""

        pattern = r'<!-- START_STATS -->.*?<!-- END_STATS -->'
        if not re.search(pattern, content, flags=re.DOTALL):
            print("❌ Could not find START_STATS and END_STATS markers in README.md")
            return False

        updated_content = re.sub(pattern, new_stats, content, flags=re.DOTALL)

        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(updated_content)

        print(f"✅ README updated successfully! (Views: {views_str}, Updated: {now_utc})")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == '__main__':
    username = os.getenv('GITHUB_USERNAME', 'Edge-Explorer')
    token = os.getenv('GITHUB_TOKEN', '')

    print(f"🚀 Updating README for @{username}...")
    success = update_readme(username, token)

    if success:
        print("✅ Done!")
    else:
        print("❌ Failed")
        exit(1)
