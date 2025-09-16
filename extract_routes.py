#!/usr/bin/env python3
import re
import subprocess

def extract_all_routes():
    """Extract all routes from the codebase using comprehensive regex"""
    routes = set()
    
    # Get all route lines
    result = subprocess.run([
        'grep', '-r', '@.*\\.route\\|@.*\\.get\\|@.*\\.post', 
        'Src/wiregate/routes/'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            if line and '__pycache__' not in line:
                # Try multiple patterns to extract route
                patterns = [
                    r"'([^']+)'",  # Single quotes
                    r'"([^"]+)"',  # Double quotes
                    r"f'([^']+)'", # F-strings
                    r'f"([^"]+)"'  # F-strings with double quotes
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        route = match.group(1)
                        if route.startswith('/'):
                            routes.add(route)
                            break
    
    return sorted(routes)

def main():
    routes = extract_all_routes()
    
    print(f"Total routes found: {len(routes)}")
    print("\nAll routes:")
    for route in routes:
        print(route)
    
    # Add /api/ prefix to routes that don't have it
    normalized_routes = set()
    for route in routes:
        if route.startswith('/api/'):
            normalized_routes.add(route)
        else:
            normalized_routes.add(f'/api{route}')
    
    print(f"\nNormalized routes (with /api/ prefix): {len(normalized_routes)}")
    for route in sorted(normalized_routes):
        print(route)

if __name__ == "__main__":
    main()
