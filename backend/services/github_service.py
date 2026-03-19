"""
GitHub API Integration Service
Real-time authenticity scoring based on GitHub profile data

Enterprise Features:
- Rate limiting with Redis caching
- Async HTTP requests
- Comprehensive error handling
- Language matching with resume skills
"""

import aiohttp
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
import asyncio
import hashlib
import json
import os

logger = logging.getLogger(__name__)

class GitHubVerificationService:
    """
    Real GitHub API integration with authenticity scoring
    
    Scoring Algorithm:
    - Repository count: 30%
    - Recent activity: 30%
    - Language match: 25%
    - Star count: 15%
    """
    
    # GitHub API configuration
    BASE_URL = "https://api.github.com"
    RATE_LIMIT_PER_HOUR = 5000  # With authentication
    CACHE_TTL_SECONDS = 3600  # 1 hour
    
    def __init__(self, api_token: Optional[str] = None, redis_client=None):
        """
        Initialize GitHub service
        
        Args:
            api_token: GitHub Personal Access Token (optional but recommended)
            redis_client: Redis client for caching
        """
        self.api_token = api_token or os.getenv('GITHUB_API_KEY', '')
        self.redis_client = redis_client
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Resume-Verification-System'
        }
        
        if self.api_token:
            self.headers['Authorization'] = f'token {self.api_token}'
            logger.info("GitHub service initialized with authentication")
        else:
            logger.warning("GitHub service initialized without token - rate limits apply")
    
    async def verify_profile(
        self, 
        username: str, 
        claimed_skills: Optional[List[str]] = None
    ) -> Dict:
        """
        Comprehensive GitHub profile verification
        
        Args:
            username: GitHub username
            claimed_skills: Skills claimed on resume (for matching)
        
        Returns:
            Complete authenticity report with scoring
        """
        try:
            # Check cache first
            cached_result = await self._get_cached_result(username)
            if cached_result:
                logger.info(f"Cache hit for GitHub user: {username}")
                return cached_result
            
            # Fetch profile data
            async with aiohttp.ClientSession() as session:
                # Parallel API requests for efficiency
                user_data, repos_data, events_data = await asyncio.gather(
                    self._fetch_user(session, username),
                    self._fetch_repositories(session, username),
                    self._fetch_recent_activity(session, username),
                    return_exceptions=True
                )
                
                # Handle errors
                if isinstance(user_data, Exception):
                    raise user_data
                if isinstance(repos_data, Exception):
                    repos_data = []
                if isinstance(events_data, Exception):
                    events_data = []

                repo_commit_count = await self._fetch_repo_commits_count(
                    session,
                    username,
                    repos_data,
                )
            
            # Extract metrics
            metrics = self._extract_metrics(user_data, repos_data, events_data, repo_commit_count)
            
            # Compute authenticity score
            score_breakdown = self._compute_authenticity_score(
                metrics, 
                claimed_skills or []
            )
            
            # Build response
            result = {
                'username': username,
                'profile_exists': True,
                'metrics': metrics,
                'score_breakdown': score_breakdown,
                'github_authenticity_score': score_breakdown['total_score'],
                'risk_level': self._determine_risk_level(score_breakdown['total_score']),
                'recommendations': self._generate_recommendations(metrics, score_breakdown),
                'verified_at': datetime.utcnow().isoformat(),
                'cache_ttl': self.CACHE_TTL_SECONDS
            }
            
            # Cache result
            await self._cache_result(username, result)
            
            logger.info(f"GitHub verification complete for {username}: score={result['github_authenticity_score']:.2f}")
            return result
            
        except aiohttp.ClientError as e:
            logger.error(f"GitHub API error for {username}: {str(e)}")
            return self._error_response(username, f"API connection error: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error verifying GitHub {username}")
            return self._error_response(username, f"Verification failed: {str(e)}")
    
    async def _fetch_user(self, session: aiohttp.ClientSession, username: str) -> Dict:
        """Fetch user profile data"""
        url = f"{self.BASE_URL}/users/{username}"
        async with session.get(url, headers=self.headers) as response:
            if response.status == 404:
                raise ValueError(f"GitHub user '{username}' not found")
            elif response.status == 403:
                raise ValueError("GitHub API rate limit exceeded")
            elif response.status != 200:
                raise ValueError(f"GitHub API error: {response.status}")
            
            return await response.json()
    
    async def _fetch_repositories(
        self, 
        session: aiohttp.ClientSession, 
        username: str,
        max_repos: int = 100
    ) -> List[Dict]:
        """Fetch user repositories"""
        url = f"{self.BASE_URL}/users/{username}/repos"
        params = {
            'sort': 'updated',
            'direction': 'desc',
            'per_page': min(max_repos, 100)
        }
        
        async with session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                logger.warning(f"Could not fetch repos for {username}: {response.status}")
                return []
            return await response.json()
    
    async def _fetch_recent_activity(
        self, 
        session: aiohttp.ClientSession, 
        username: str,
        max_events: int = 100
    ) -> List[Dict]:
        """Fetch recent activity events"""
        url = f"{self.BASE_URL}/users/{username}/events/public"
        params = {'per_page': min(max_events, 100)}
        
        async with session.get(url, headers=self.headers, params=params) as response:
            if response.status != 200:
                logger.warning(f"Could not fetch events for {username}: {response.status}")
                return []
            return await response.json()
    
    def _extract_metrics(
        self, 
        user_data: Dict, 
        repos_data: List[Dict],
        events_data: List[Dict],
        repo_commit_count: int,
    ) -> Dict:
        """Extract key metrics from API data"""
        # Repository metrics
        total_repos = len(repos_data)
        public_repos = user_data.get('public_repos', 0)
        total_stars = sum(repo.get('stargazers_count', 0) for repo in repos_data)
        total_forks = sum(repo.get('forks_count', 0) for repo in repos_data)
        
        # Language analysis
        languages = []
        for repo in repos_data:
            lang = repo.get('language')
            if lang:
                languages.append(lang)
        
        language_distribution = Counter(languages)
        top_languages = [lang for lang, _ in language_distribution.most_common(5)]
        
        # Activity metrics
        account_age_days = self._calculate_account_age(user_data.get('created_at', ''))
        last_activity = self._get_last_activity_date(repos_data, events_data)
        days_since_activity = (datetime.utcnow() - last_activity).days if last_activity else None
        
        # Contribution frequency (commits from events)
        commit_count = sum(
            1 for event in events_data 
            if event.get('type') == 'PushEvent'
        )
        total_recent_commits = commit_count + repo_commit_count
        
        # Repository quality indicators
        repos_with_description = sum(1 for repo in repos_data if repo.get('description'))
        repos_with_readme = sum(
            1 for repo in repos_data 
            if repo.get('has_wiki') or repo.get('has_pages')
        )
        
        return {
            'public_repos': public_repos,
            'total_stars': total_stars,
            'total_forks': total_forks,
            'top_languages': top_languages,
            'language_distribution': dict(language_distribution),
            'account_age_days': account_age_days,
            'days_since_last_activity': days_since_activity,
            'recent_event_commit_count': commit_count,
            'recent_repo_commit_count': repo_commit_count,
            'recent_commit_count': total_recent_commits,
            'repos_with_description': repos_with_description,
            'avg_stars_per_repo': round(total_stars / max(total_repos, 1), 2),
            'profile_complete': bool(user_data.get('bio') and user_data.get('location')),
            'followers': user_data.get('followers', 0),
            'following': user_data.get('following', 0),
            'hireable': user_data.get('hireable', False)
        }

    async def _fetch_repo_commits_count(
        self,
        session: aiohttp.ClientSession,
        username: str,
        repos_data: List[Dict],
        max_repos: int = 5,
    ) -> int:
        """Estimate recent commit volume by sampling top updated repositories."""
        if not repos_data:
            return 0

        tasks = []
        for repo in repos_data[:max_repos]:
            repo_name = repo.get("name")
            if not repo_name:
                continue
            url = f"{self.BASE_URL}/repos/{username}/{repo_name}/commits"
            params = {"per_page": 30}
            tasks.append(session.get(url, headers=self.headers, params=params))

        if not tasks:
            return 0

        count = 0
        for coro in asyncio.as_completed(tasks):
            try:
                response = await coro
                async with response:
                    if response.status == 200:
                        commits = await response.json()
                        if isinstance(commits, list):
                            count += len(commits)
            except Exception:
                continue
        return count
    
    def _compute_authenticity_score(
        self, 
        metrics: Dict, 
        claimed_skills: List[str]
    ) -> Dict:
        """
        Compute GitHub authenticity score with breakdown
        
        Scoring weights:
        - Repository count: 30%
        - Recent activity: 30%
        - Language match: 25%
        - Star/social proof: 15%
        """
        scores = {}
        
        # 1. Repository Score (30%)
        repo_score = self._score_repositories(metrics['public_repos'])
        scores['repository_score'] = repo_score * 0.30
        
        # 2. Activity Score (30%)
        activity_score = self._score_activity(
            metrics['days_since_last_activity'],
            metrics['recent_commit_count'],
            metrics['account_age_days']
        )
        scores['activity_score'] = activity_score * 0.30
        
        # 3. Language Match Score (25%)
        language_score = self._score_language_match(
            metrics['top_languages'],
            claimed_skills
        )
        scores['language_match_score'] = language_score * 0.25
        
        # 4. Social Proof Score (15%)
        social_score = self._score_social_proof(
            metrics['total_stars'],
            metrics['followers'],
            metrics['total_forks']
        )
        scores['social_proof_score'] = social_score * 0.15
        
        # Total score (0-100)
        total_score = sum(scores.values())
        
        return {
            'repo_score': round(repo_score, 2),
            'activity_score': round(activity_score, 2),
            'language_match_score': round(language_score, 2),
            'social_proof_score': round(social_score, 2),
            'weighted_breakdown': {k: round(v, 2) for k, v in scores.items()},
            'total_score': round(total_score, 2),
            'max_score': 100.0
        }
    
    def _score_repositories(self, count: int) -> float:
        """Score based on repository count (0-100)"""
        if count >= 50:
            return 100.0
        elif count >= 30:
            return 90.0
        elif count >= 20:
            return 80.0
        elif count >= 10:
            return 70.0
        elif count >= 5:
            return 60.0
        elif count >= 3:
            return 50.0
        elif count >= 1:
            return 40.0
        else:
            return 0.0
    
    def _score_activity(
        self, 
        days_since_activity: Optional[int],
        commit_count: int,
        account_age_days: int
    ) -> float:
        """Score based on recent activity (0-100)"""
        if days_since_activity is None:
            return 0.0
        
        # Recency score
        if days_since_activity <= 7:
            recency = 100.0
        elif days_since_activity <= 30:
            recency = 90.0
        elif days_since_activity <= 90:
            recency = 75.0
        elif days_since_activity <= 180:
            recency = 60.0
        elif days_since_activity <= 365:
            recency = 40.0
        else:
            recency = 20.0
        
        # Commit frequency score
        if commit_count >= 20:
            frequency = 100.0
        elif commit_count >= 10:
            frequency = 80.0
        elif commit_count >= 5:
            frequency = 60.0
        elif commit_count >= 1:
            frequency = 40.0
        else:
            frequency = 20.0
        
        # Account maturity bonus
        maturity_bonus = min(20, account_age_days / 365 * 10)
        
        return min(100.0, (recency * 0.5 + frequency * 0.4 + maturity_bonus * 0.1))
    
    def _score_language_match(
        self, 
        github_languages: List[str],
        claimed_skills: List[str]
    ) -> float:
        """Score based on language/skill matching (0-100)"""
        if not claimed_skills:
            # No skills claimed - neutral score
            return 50.0
        
        # Normalize languages for comparison
        github_langs_normalized = {lang.lower() for lang in github_languages}
        claimed_skills_normalized = {skill.lower() for skill in claimed_skills}
        
        # Check for programming language matches
        programming_langs = {
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 
            'go', 'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala',
            'html', 'css', 'sql', 'shell', 'bash', 'r', 'matlab'
        }
        
        claimed_lang_skills = claimed_skills_normalized & programming_langs
        
        if not claimed_lang_skills:
            # No programming skills claimed - neutral
            return 50.0
        
        # Calculate match percentage
        matches = github_langs_normalized & claimed_lang_skills
        match_percentage = len(matches) / len(claimed_lang_skills)
        
        # Convert to 0-100 score
        if match_percentage >= 0.8:
            return 100.0
        elif match_percentage >= 0.6:
            return 85.0
        elif match_percentage >= 0.4:
            return 70.0
        elif match_percentage >= 0.2:
            return 55.0
        elif match_percentage > 0:
            return 40.0
        else:
            return 25.0  # No matches - suspicious
    
    def _score_social_proof(
        self, 
        stars: int, 
        followers: int,
        forks: int
    ) -> float:
        """Score based on social proof metrics (0-100)"""
        # Weighted combination
        star_score = min(100, stars / 10 * 100) * 0.5
        follower_score = min(100, followers / 5 * 100) * 0.3
        fork_score = min(100, forks / 5 * 100) * 0.2
        
        return star_score + follower_score + fork_score
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score"""
        if score >= 80:
            return "Low"
        elif score >= 60:
            return "Medium"
        elif score >= 40:
            return "High"
        else:
            return "Critical"
    
    def _generate_recommendations(self, metrics: Dict, score_breakdown: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        if metrics['public_repos'] < 5:
            recommendations.append("Limited repository presence - verify other credentials")
        
        if metrics['days_since_last_activity'] and metrics['days_since_last_activity'] > 180:
            recommendations.append("Account inactive for 6+ months - verify current skills")
        
        if score_breakdown['language_match_score'] < 40:
            recommendations.append("Programming languages don't match claimed skills")
        
        if metrics['total_stars'] == 0 and metrics['followers'] == 0:
            recommendations.append("No community engagement - verify experience level")
        
        if not metrics['profile_complete']:
            recommendations.append("Incomplete profile - may indicate low engagement")
        
        if not recommendations:
            recommendations.append("GitHub profile aligns well with resume claims")
        
        return recommendations
    
    def _calculate_account_age(self, created_at: str) -> int:
        """Calculate account age in days"""
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return (datetime.utcnow() - created_date.replace(tzinfo=None)).days
        except:
            return 0
    
    def _get_last_activity_date(
        self, 
        repos: List[Dict],
        events: List[Dict]
    ) -> Optional[datetime]:
        """Get most recent activity date"""
        dates = []
        
        # Check repository updates
        for repo in repos:
            if repo.get('updated_at'):
                try:
                    date = datetime.fromisoformat(repo['updated_at'].replace('Z', '+00:00'))
                    dates.append(date.replace(tzinfo=None))
                except:
                    pass
        
        # Check event timestamps
        for event in events:
            if event.get('created_at'):
                try:
                    date = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
                    dates.append(date.replace(tzinfo=None))
                except:
                    pass
        
        return max(dates) if dates else None
    
    async def _get_cached_result(self, username: str) -> Optional[Dict]:
        """Retrieve cached result from Redis"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(username)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis cache retrieval error: {e}")
        
        return None
    
    async def _cache_result(self, username: str, result: Dict):
        """Store result in Redis cache"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._get_cache_key(username)
            await self.redis_client.setex(
                cache_key,
                self.CACHE_TTL_SECONDS,
                json.dumps(result)
            )
        except Exception as e:
            logger.warning(f"Redis cache storage error: {e}")
    
    def _get_cache_key(self, username: str) -> str:
        """Generate cache key for username"""
        return f"github:verify:{username.lower()}"
    
    def _error_response(self, username: str, error_message: str) -> Dict:
        """Generate error response"""
        return {
            'username': username,
            'profile_exists': False,
            'error': error_message,
            'github_authenticity_score': 0.0,
            'risk_level': 'Critical',
            'verified_at': datetime.utcnow().isoformat()
        }


# Singleton instance
_github_service: Optional[GitHubVerificationService] = None

def get_github_service(
    api_token: Optional[str] = None,
    redis_client=None
) -> GitHubVerificationService:
    """Get or create GitHub service instance"""
    global _github_service
    
    if _github_service is None:
        _github_service = GitHubVerificationService(api_token, redis_client)
    
    return _github_service
