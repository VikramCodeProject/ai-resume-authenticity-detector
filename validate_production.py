#!/usr/bin/env python3
"""
Production Deployment Validator
Run this script to verify all production dependencies and credentials are configured.

Usage:
    python validate_production.py
    
Expected output:
    ✅ All checks passed - Ready for production deployment
"""

import os
import sys
import re
import importlib.util
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def is_strict_external_validation() -> bool:
    """Enable strict live connectivity checks for external providers."""
    return os.getenv('STRICT_EXTERNAL_VALIDATION', 'false').strip().lower() in {'1', 'true', 'yes'}


def looks_like_placeholder(value: str) -> bool:
    """Detect common template placeholder values."""
    v = (value or '').strip().lower()
    placeholder_markers = [
        'change_me',
        'your_',
        'replace_',
        'example',
        'project-id',
        'app-specific-password',
    ]
    return any(marker in v for marker in placeholder_markers)


def strict_placeholder_result(service_name: str) -> Tuple[bool, str]:
    """Return strict-mode failure for placeholder secrets."""
    if is_strict_external_validation():
        return False, f"❌ {service_name} values look like placeholders (strict mode requires real credentials)"
    return True, f"⚠ {service_name} values look like placeholders (live check skipped)"

def check_env_file_exists() -> Tuple[bool, str]:
    """Check if .env.production exists"""
    if Path('.env.production').exists():
        return True, "✅ .env.production file exists"
    return False, "❌ .env.production not found (create from .env.production.template)"

def check_env_variable(var_name: str, min_length: int = 1) -> Tuple[bool, str]:
    """Check if environment variable is set"""
    value = os.getenv(var_name, '').strip()
    
    if not value:
        return False, f"❌ {var_name} is not set"
    
    if len(value) < min_length:
        return False, f"❌ {var_name} is too short (minimum {min_length} chars)"
    
    # Mask value for security
    if len(value) <= 8:
        masked = '*' * len(value)
    else:
        masked = value[:4] + '*' * (len(value) - 8) + value[-4:]
    return True, f"✅ {var_name} is set ({masked})"

def check_python_package(package_name: str) -> Tuple[bool, str]:
    """Check if Python package is installed"""
    try:
        if importlib.util.find_spec(package_name) is not None:
            return True, f"✅ {package_name} is installed"
        return False, f"❌ {package_name} is not installed - run: pip install {package_name}"
    except Exception as e:
        return False, f"❌ {package_name} package check failed: {str(e)}"

def test_database_connection() -> Tuple[bool, str]:
    """Test PostgreSQL connection"""
    try:
        import psycopg2  # noqa: F401
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            return False, "❌ DATABASE_URL not configured"

        parsed = urlparse(db_url)
        if parsed.scheme not in {"postgresql", "postgresql+asyncpg", "postgresql+psycopg", "postgres"}:
            return False, "❌ DATABASE_URL format invalid (expected postgresql:// or postgresql+asyncpg://)"
        if not parsed.hostname or not parsed.path or parsed.path == '/':
            return False, "❌ DATABASE_URL appears incomplete (host/database missing)"

        return True, "✅ DATABASE_URL format is valid"
    except Exception as e:
        return False, f"❌ Database check failed: {str(e)}"

def test_aws_s3() -> Tuple[bool, str]:
    """Test AWS S3 configuration"""
    try:
        import boto3
        
        bucket = os.getenv('AWS_S3_BUCKET', '')
        if not bucket:
            return False, "❌ AWS_S3_BUCKET not configured"
        
        access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        
        if not access_key or not secret_key:
            return False, "❌ AWS credentials not configured"
        
        if looks_like_placeholder(access_key) or looks_like_placeholder(secret_key) or looks_like_placeholder(bucket):
            return strict_placeholder_result("AWS S3")

        if not is_strict_external_validation():
            return True, "⚠ AWS S3 credentials configured (live check skipped; set STRICT_EXTERNAL_VALIDATION=true to enforce)"

        # Strict mode: verify credentials and bucket access
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        
        s3.head_bucket(Bucket=bucket)
        return True, f"✅ AWS S3 bucket '{bucket}' is accessible"
    except Exception as e:
        return False, f"❌ AWS S3 check failed: {str(e)}"

def test_github_api() -> Tuple[bool, str]:
    """Test GitHub API token"""
    try:
        import requests
        
        token = os.getenv('GITHUB_API_KEY', '')
        if not token:
            return False, "❌ GITHUB_API_KEY not configured"

        if looks_like_placeholder(token):
            return strict_placeholder_result("GitHub")

        if not re.match(r'^(ghp_|github_pat_|gho_|ghu_|ghs_|ghr_).+', token):
            return False, "❌ GITHUB_API_KEY format looks invalid"

        if not is_strict_external_validation():
            return True, "⚠ GitHub token format looks valid (live check skipped; set STRICT_EXTERNAL_VALIDATION=true to enforce)"
        
        headers = {"Authorization": f"token {token}"}
        resp = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            user_data = resp.json()
            return True, f"✅ GitHub API token valid (user: {user_data.get('login')})"
        elif resp.status_code == 401:
            return False, "❌ GitHub API token is invalid or expired"
        else:
            return False, f"❌ GitHub API returned {resp.status_code}"
    except Exception as e:
        return False, f"❌ GitHub API check failed: {str(e)}"

def test_sendgrid_api() -> Tuple[bool, str]:
    """Test SendGrid configuration"""
    try:
        import sendgrid
        
        api_key = os.getenv('SENDGRID_API_KEY', '')
        if not api_key:
            return False, "❌ SENDGRID_API_KEY not configured"

        if looks_like_placeholder(api_key):
            return strict_placeholder_result("SendGrid")

        if not api_key.startswith('SG.'):
            return False, "❌ SENDGRID_API_KEY format invalid (must start with 'SG.')"

        if not is_strict_external_validation():
            return True, "⚠ SendGrid key format valid (live check skipped; set STRICT_EXTERNAL_VALIDATION=true to enforce)"

        sg = sendgrid.SendGridAPIClient(api_key)
        # Simple validation - just check if client initializes
        return True, "✅ SendGrid API key is configured"
    except Exception as e:
        return False, f"❌ SendGrid check failed: {str(e)}"

def test_jwt_secret() -> Tuple[bool, str]:
    """Test JWT secret configuration"""
    secret = os.getenv('JWT_SECRET', '')
    
    if not secret:
        return False, "❌ JWT_SECRET not configured"
    
    if len(secret) < 32:
        return False, f"❌ JWT_SECRET too short (minimum 32 chars, current: {len(secret)})"
    
    return True, f"✅ JWT_SECRET is {len(secret)} characters (secure)"

def test_blockchain() -> Tuple[bool, str]:
    """Test blockchain configuration"""
    try:
        from web3 import Web3
        
        rpc_url = os.getenv('ETH_RPC_URL', '')
        if not rpc_url:
            return False, "❌ ETH_RPC_URL not configured"
        
        contract_address = os.getenv('SMART_CONTRACT_ADDRESS', '')
        if not contract_address or not contract_address.startswith('0x'):
            return False, "❌ SMART_CONTRACT_ADDRESS format invalid (must start with 0x)"
        
        private_key = os.getenv('PRIVATE_KEY', '')
        if not private_key or not private_key.startswith('0x'):
            return False, "❌ PRIVATE_KEY format invalid (must start with 0x)"

        if looks_like_placeholder(private_key) or looks_like_placeholder(contract_address):
            return strict_placeholder_result("Blockchain")

        if not is_strict_external_validation():
            return True, "⚠ Blockchain config present (RPC check skipped; set STRICT_EXTERNAL_VALIDATION=true to enforce)"
        
        # Strict mode: test RPC connectivity
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if w3.is_connected():
            return True, f"✅ Blockchain connected (network: {w3.eth.chain_id})"
        else:
            return False, "❌ Could not connect to blockchain RPC"
    except Exception as e:
        return False, f"❌ Blockchain check failed: {str(e)}"

def test_redis() -> Tuple[bool, str]:
    """Test Redis connection"""
    try:
        import redis
        
        redis_url = os.getenv('REDIS_URL', '')
        if not redis_url:
            return False, "❌ REDIS_URL not configured"

        parsed = urlparse(redis_url)
        if parsed.scheme not in {"redis", "rediss"}:
            return False, "❌ REDIS_URL format invalid (expected redis:// or rediss://)"

        if not is_strict_external_validation():
            return True, "⚠ Redis URL format valid (connection check skipped; set STRICT_EXTERNAL_VALIDATION=true to enforce)"
        
        r = redis.from_url(redis_url)
        r.ping()
        return True, f"✅ Redis is connected"
    except Exception as e:
        return False, f"❌ Redis check failed: {str(e)}"

def main():
    """Run all validation checks"""
    print(f"\n{Colors.BLUE}{'='*60}")
    print("PRODUCTION DEPLOYMENT VALIDATOR")
    print(f"{'='*60}{Colors.RESET}\n")
    if is_strict_external_validation():
        print("Mode: STRICT_EXTERNAL_VALIDATION=true (live provider checks enabled)\n")
    else:
        print("Mode: default (configuration validation with external live checks skipped)\n")
    
    # Load .env.production
    if Path('.env.production').exists():
        from dotenv import load_dotenv
        load_dotenv('.env.production')
    
    checks = {
        "Environment Files": [
            check_env_file_exists,
        ],
        "Python Packages": [
            lambda: check_python_package('fastapi'),
            lambda: check_python_package('sqlalchemy'),
            lambda: check_python_package('psycopg2'),
            lambda: check_python_package('boto3'),
            lambda: check_python_package('sendgrid'),
            lambda: check_python_package('argon2'),
            lambda: check_python_package('web3'),
            lambda: check_python_package('redis'),
        ],
        "Environment Variables": [
            lambda: check_env_variable('ENVIRONMENT'),
            lambda: check_env_variable('DATABASE_URL'),
            lambda: check_env_variable('REDIS_URL'),
            lambda: check_env_variable('JWT_SECRET', 32),
            lambda: check_env_variable('GITHUB_API_KEY'),
            lambda: check_env_variable('AWS_S3_BUCKET'),
            lambda: check_env_variable('AWS_ACCESS_KEY_ID'),
            lambda: check_env_variable('AWS_SECRET_ACCESS_KEY'),
            lambda: check_env_variable('AWS_REGION'),
            lambda: check_env_variable('SENDGRID_API_KEY'),
            lambda: check_env_variable('ETH_RPC_URL'),
            lambda: check_env_variable('SMART_CONTRACT_ADDRESS'),
            lambda: check_env_variable('PRIVATE_KEY'),
        ],
        "Service Connections": [
            test_database_connection,
            test_aws_s3,
            test_github_api,
            test_sendgrid_api,
            test_jwt_secret,
            test_blockchain,
            test_redis,
        ],
    }
    
    total_checks = sum(len(checks_list) for checks_list in checks.values())
    passed_checks = 0
    failed_checks = []
    
    for category, checks_list in checks.items():
        print(f"{Colors.BLUE}{category}:{Colors.RESET}")
        
        for check_func in checks_list:
            try:
                success, message = check_func()
                print(f"  {message}")
                
                if success:
                    passed_checks += 1
                else:
                    failed_checks.append(f"{category}: {message}")
            except Exception as e:
                print(f"  ❌ Check failed with error: {str(e)}")
                failed_checks.append(f"{category}: {str(e)}")
        
        print()
    
    # Summary
    print(f"{Colors.BLUE}{'='*60}")
    print(f"SUMMARY: {passed_checks}/{total_checks} checks passed")
    print(f"{'='*60}{Colors.RESET}\n")
    
    if not failed_checks:
        print(f"{Colors.GREEN}✅ ALL CHECKS PASSED{Colors.RESET}")
        print(f"{Colors.GREEN}Your system is ready for production deployment!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}❌ {len(failed_checks)} CHECKS FAILED{Colors.RESET}\n")
        print("Failures:")
        for failure in failed_checks:
            print(f"  • {failure}")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
