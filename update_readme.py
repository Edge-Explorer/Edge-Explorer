#!/usr/bin/env python3
"""
GitHub Stats README Updater
Automatically updates README.md with latest GitHub statistics
"""

import os
import re
import requests
from datetime import datetime
from typing import Dict, Any

class GitHubStatsUpdater:
    def __init__(self, username: str, token: str):
        self.username = username
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.base_url = 'https://api.github.com'
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Fetch GitHub user statistics"""
        try:
            response = requests.get(
                f'{self.base_url}/users/{self.username}',
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching user stats: {e}")
            return {}
    
    def get_repos_stats(self) -> Dict[str, Any]:
        """Fetch repository statistics"""
        try:
            response = requests.get(
                f'{self.base_url}/users/{self.username}/repos',
                headers=self.headers,
                params={'per_page': 100, 'type': 'owner'},
                timeout=10
            )
            response.raise_for_status()
            repos = response.json()
            
            total_commits = 0
            total_stars = sum(repo.get('stargazers_count', 0) for repo in repos)
            total_forks = sum(repo.get('forks_count', 0) for repo in repos)
            
            # Count commits across repositories
            for repo in repos:
                try:
                    commit_response = requests.get(
                        f'{self.base_url}/repos/{self.username}/{repo["name"]}/commits',
                        headers=self.headers,
                        params={'per_page': 1},
                        timeout=10
                    )
                    if commit_response.status_code == 200:
                        # Get total commit count from Link header
                        link_header = commit_response.headers.get('Link', '')
                        if 'last' in link_header:
                            match = re.search(r'page=(\d+)>; rel="last"', link_header)
                            if match:
                                total_commits += int(match.group(1))
                        elif len(commit_response.json()) > 0:
                            total_commits += 1
                except:
                    pass
            
            return {
                'repos_count': len(repos),
                'public_repos': sum(1 for r in repos if not r.get('private', False)),
                'total_stars': total_stars,
                'total_forks': total_forks,
                'total_commits': total_commits,
                'followers': self.get_user_stats().get('followers', 0),
                'following': self.get_user_stats().get('following', 0)
            }
        except requests.exceptions.RequestException as e:
            print(f"Error fetching repos stats: {e}")
            return {}
    
    def get_languages(self) -> Dict[str, float]:
        """Get most used programming languages"""
        try:
            response = requests.get(
                f'{self.base_url}/users/{self.username}/repos',
                headers=self.headers,
                params={'per_page': 100, 'type': 'owner'},
                timeout=10
            )
            response.raise_for_status()
            repos = response.json()
            
            language_bytes = {}
            
            for repo in repos:
                if repo.get('language'):
                    lang_response = requests.get(
                        f'{self.base_url}/repos/{self.username}/{repo["name"]}/languages',
                        headers=self.headers,
                        timeout=10
                    )
                    if lang_response.status_code == 200:
                        languages = lang_response.json()
                        for lang, bytes_count in languages.items():
                            language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count
            
            # Calculate percentages
            total_bytes = sum(language_bytes.values())
            if total_bytes == 0:
                return {}
            
            language_percentages = {
                lang: round((bytes_count / total_bytes) * 100, 1)
                for lang, bytes_count in language_bytes.items()
            }
            
            # Sort by percentage and return top 10
            return dict(sorted(
                language_percentages.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching languages: {e}")
            return {}
    
    def generate_language_bars(self, languages: Dict[str, float]) -> str:
        """Generate ASCII bar chart for languages"""
        if not languages:
            return "Unable to fetch language data"
        
        bars = []
        for lang, percentage in languages.items():
            filled = int(percentage / 2)  # Convert to 50-char bar
            empty = 50 - filled
            bar = f"{lang:15} {'█' * filled}{'░' * empty} {percentage:.1f}%"
            bars.append(bar)
        
        return "\n".join(bars)
    
    def generate_readme_stats(self) -> str:
        """Generate the statistics section for README"""
        stats = self.get_repos_stats()
        languages = self.get_languages()
        user_info = self.get_user_stats()
        
        if not stats:
            return ""
        
        # Streak data (static for now, but you can add API call if needed)
        current_date = datetime.now()
        
        stats_section = f"""## 📊 GitHub Statistics

<div align="center">

| Metric | Value |
|--------|-------|
| **Total Repositories** | {stats.get('public_repos', 0)} Public |
| **Total Commits** | {stats.get('total_commits', 0)}+ |
| **Total Stars** | ⭐ {stats.get('total_stars', 0)} |
| **Total Forks** | 🍴 {stats.get('total_forks', 0)} |
| **Followers** | 👥 {stats.get('followers', 0)} |
| **Following** | 👤 {stats.get('following', 0)} |
| **Last Updated** | {current_date.strftime('%B %d, %Y')} |

</div>

### 🏆 Top Technologies
