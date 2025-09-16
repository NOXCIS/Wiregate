#!/usr/bin/env python3
"""
API Documentation Verification Script
Compares all routes in the codebase against the API documentation
Handles the /api/ prefix that gets added when the application is running
"""

import os
import re
import subprocess
from pathlib import Path

def extract_routes_from_codebase():
    """Extract all API routes from the codebase"""
    routes = set()
    
    # Use a simpler approach - search for route patterns
    cmd = "grep -r '@.*\\.route\\|@.*\\.get\\|@.*\\.post' Src/wiregate/routes/"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            if line:
                # Extract the route path from the line
                # Look for patterns like '/api/endpoint' or '/endpoint' in both single and double quotes
                match = re.search(r"'([^']+)'", line)
                if not match:
                    match = re.search(r'"([^"]+)"', line)
                
                if match:
                    route = match.group(1)
                    # Add /api/ prefix if it doesn't have it (since all routes get this prefix when running)
                    if route.startswith('/') and not route.startswith('/api/'):
                        route = '/api' + route
                    elif route.startswith('/api/'):
                        pass  # Already has /api/ prefix
                    else:
                        continue  # Skip non-route patterns
                    routes.add(route)
    
    return sorted(routes)

def extract_routes_from_docs():
    """Extract all API routes from the documentation"""
    routes = set()
    
    # Read the documentation file
    doc_path = 'Docs/API_DOCUMENTATION.md'
    if os.path.exists(doc_path):
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all route patterns in the documentation
        # Look for patterns like "GET /api/endpoint" or "POST /api/endpoint"
        pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+(/api/[^\s\]]+)'
        matches = re.findall(pattern, content)
        
        for method, route in matches:
            # Clean up the route (remove query parameters, etc.)
            route = route.split('?')[0].split('#')[0]
            routes.add(route)
    
    return sorted(routes)

def check_route_in_docs(route, doc_routes):
    """Check if a specific route exists in documentation"""
    # Direct match
    if route in doc_routes:
        return True
    
    # Check for routes with/without trailing slashes
    route_no_slash = route.rstrip('/')
    route_with_slash = route + '/' if not route.endswith('/') else route
    
    for doc_route in doc_routes:
        doc_route_no_slash = doc_route.rstrip('/')
        doc_route_with_slash = doc_route + '/' if not doc_route.endswith('/') else doc_route
        
        # Check exact matches with/without slashes
        if (route_no_slash == doc_route_no_slash or 
            route_with_slash == doc_route_with_slash or
            route_no_slash == doc_route_with_slash or
            route_with_slash == doc_route_no_slash):
            return True
        
        # Check for parameterized routes (e.g., /api/endpoint/<param>)
        if (route_no_slash.replace('<', '').replace('>', '') in doc_route_no_slash.replace('<', '').replace('>', '') or
            route_with_slash.replace('<', '').replace('>', '') in doc_route_with_slash.replace('<', '').replace('>', '')):
            return True
    
    return False

def main():
    print("🔍 API Documentation Verification Script")
    print("=" * 50)
    print("ℹ️  Note: All routes get /api/ prefix when the application is running")
    print()
    
    # Extract routes from codebase
    print("📂 Extracting routes from codebase...")
    codebase_routes = extract_routes_from_codebase()
    print(f"   Found {len(codebase_routes)} routes in codebase")
    
    # Extract routes from documentation
    print("📚 Extracting routes from documentation...")
    doc_routes = extract_routes_from_docs()
    print(f"   Found {len(doc_routes)} routes in documentation")
    
    print("\n🔍 Comparing routes...")
    
    # Check each codebase route against documentation
    missing_routes = []
    documented_routes = []
    
    for route in codebase_routes:
        if check_route_in_docs(route, doc_routes):
            documented_routes.append(route)
        else:
            missing_routes.append(route)
    
    # Check for extra routes in documentation (not in codebase)
    extra_routes = []
    for doc_route in doc_routes:
        found = False
        for code_route in codebase_routes:
            if code_route.replace('<', '').replace('>', '') in doc_route.replace('<', '').replace('>', ''):
                found = True
                break
        if not found:
            extra_routes.append(doc_route)
    
    # Print results
    print(f"\n✅ DOCUMENTED ROUTES: {len(documented_routes)}")
    print(f"❌ MISSING ROUTES: {len(missing_routes)}")
    print(f"⚠️  EXTRA ROUTES: {len(extra_routes)}")
    
    if missing_routes:
        print(f"\n❌ MISSING ROUTES ({len(missing_routes)}):")
        for route in missing_routes:
            print(f"   - {route}")
    
    if extra_routes:
        print(f"\n⚠️  EXTRA ROUTES IN DOCS ({len(extra_routes)}):")
        for route in extra_routes:
            print(f"   - {route}")
    
    # Calculate completeness percentage
    total_routes = len(codebase_routes)
    documented_count = len(documented_routes)
    completeness = (documented_count / total_routes * 100) if total_routes > 0 else 0
    
    print(f"\n📊 COMPLETENESS: {completeness:.1f}% ({documented_count}/{total_routes})")
    
    if completeness == 100:
        print("🎉 API Documentation is 100% COMPLETE!")
    elif completeness >= 95:
        print("✅ API Documentation is nearly complete!")
    elif completeness >= 90:
        print("⚠️  API Documentation is mostly complete but has some gaps")
    else:
        print("❌ API Documentation needs significant updates")
    
    # Check for duplicates in documentation
    print(f"\n🔍 Checking for duplicates in documentation...")
    doc_route_counts = {}
    for route in doc_routes:
        doc_route_counts[route] = doc_route_counts.get(route, 0) + 1
    
    duplicates = {route: count for route, count in doc_route_counts.items() if count > 1}
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate routes in documentation:")
        for route, count in duplicates.items():
            print(f"   - {route} (appears {count} times)")
    else:
        print("✅ No duplicates found in documentation")
    
    # Show some examples of routes found
    print(f"\n📋 SAMPLE ROUTES FROM CODEBASE:")
    for i, route in enumerate(codebase_routes[:10]):
        print(f"   {i+1:2d}. {route}")
    if len(codebase_routes) > 10:
        print(f"   ... and {len(codebase_routes) - 10} more")
    
    return completeness == 100 and len(duplicates) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
