#!/usr/bin/env python3
"""
Simple GitHub Stats README Updater
"""
import os
import re
import requests
from datetime import datetime

def get_github_stats(username, token):
    """Fetch GitHub statistics"""
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Get user info
        user_resp = requests.get(f'https://api.github.com/users/{username}', 
                                 headers=headers, timeout=10)
        user_data = user_resp.json()
        
        # Get repos
        repos_resp = requests.get(f'https://api.github.com/users/{username}/repos',
                                  headers=headers, params={'per_page': 100}, timeout=10)
        repos = repos_resp.json()
        
        public_repos = len([r for r in repos if not r.get('private')])
        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        total_forks = sum(r.get('forks_count', 0) for r in repos)
        
        return {
            'repos': public_repos,
            'stars': total_stars,
            'forks': total_forks,
            'followers': user_data.get('followers', 0),
            'following': user_data.get('following', 0)
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return None

def update_readme(username, token):
    """Update README with GitHub stats"""
    
    stats = get_github_stats(username, token)
    if not stats:
        print("Failed to get stats")
        return False
    
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create new stats section
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
| **Last Updated** | {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')} |

</div>
<!-- END_STATS -->"""
        
        # Find and replace the stats section using markers
        pattern = r'<!-- START_STATS -->.*?<!-- END_STATS -->'
        if not re.search(pattern, content, flags=re.DOTALL):
            print("❌ Could not find START_STATS and END_STATS markers in README.md")
            return False
            
        updated_content = re.sub(pattern, new_stats, content, flags=re.DOTALL)
        
        # Write back
        with open('README.md', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ README updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    username = os.getenv('GITHUB_USERNAME', 'Edge-Explorer')
    token = os.getenv('GITHUB_TOKEN')
    
    if not token:
        print("❌ No GitHub token found")
        exit(1)
    
    print(f"🚀 Updating README for @{username}...")
    success = update_readme(username, token)
    
    if success:
        print("✅ Done!")
    else:
        print("❌ Failed")
        exit(1)
