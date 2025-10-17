#!/usr/bin/env python3
"""
ArcGIS OAuth 2.0 Authentication Script
This script demonstrates how to authenticate with ArcGIS using OAuth 2.0
"""

import os
import requests
import json
import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class ArcGISAuth:
    def __init__(self, client_id, client_secret, redirect_uri="http://localhost:8080"):
        """
        Initialize ArcGIS OAuth client
        
        Args:
            client_id: Your ArcGIS application client ID
            client_secret: Your ArcGIS application client secret
            redirect_uri: The redirect URI configured in your app (default: http://localhost:8080)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://www.arcgis.com"
        self.auth_code = None
        self.access_token = None
        self.refresh_token = None
        self.expires_in = None
        
    def get_authorization_url(self):
        """Generate the authorization URL for user consent"""
        auth_endpoint = f"{self.base_url}/sharing/rest/oauth2/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "expiration": 20160,  # 2 weeks in minutes
        }
        return f"{auth_endpoint}?{urlencode(params)}"
    
    def start_local_server(self, port=8080):
        """Start a local server to capture the authorization code"""
        class AuthHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                # Parse the authorization code from the callback URL
                query = urlparse(handler_self.path).query
                params = parse_qs(query)
                
                if 'code' in params:
                    self.auth_code = params['code'][0]
                    handler_self.send_response(200)
                    handler_self.send_header('Content-type', 'text/html')
                    handler_self.end_headers()
                    handler_self.wfile.write(b"""
                        <html>
                        <body>
                        <h1>Authorization Successful!</h1>
                        <p>You can close this window and return to the application.</p>
                        </body>
                        </html>
                    """)
                else:
                    handler_self.send_response(400)
                    handler_self.send_header('Content-type', 'text/html')
                    handler_self.end_headers()
                    handler_self.wfile.write(b"Authorization failed: No code received")
                
            def log_message(self, format, *args):
                # Suppress server log messages
                pass
        
        server = HTTPServer(('localhost', port), AuthHandler)
        server.timeout = 60  # 60 second timeout
        server.handle_request()  # Handle one request then stop
        
    def authorize(self):
        """Complete the OAuth authorization flow"""
        # Step 1: Open browser for user authorization
        auth_url = self.get_authorization_url()
        print(f"Opening browser for authorization...")
        print(f"If browser doesn't open, visit: {auth_url}")
        webbrowser.open(auth_url)
        
        # Step 2: Start local server to receive callback
        print("Waiting for authorization...")
        self.start_local_server()
        
        if not self.auth_code:
            raise Exception("Failed to receive authorization code")
        
        print(f"Authorization code received: {self.auth_code[:10]}...")
        
        # Step 3: Exchange authorization code for access token
        self.exchange_code_for_token()
        
    def exchange_code_for_token(self):
        """Exchange authorization code for access token"""
        token_endpoint = f"{self.base_url}/sharing/rest/oauth2/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": self.auth_code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(token_endpoint, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            self.expires_in = token_data.get("expires_in")
            
            print("✓ Access token obtained successfully!")
            print(f"  Token: {self.access_token[:20]}...")
            print(f"  Expires in: {self.expires_in} seconds")
            
            return token_data
        else:
            raise Exception(f"Failed to exchange code for token: {response.text}")
    
    def refresh_access_token(self):
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        token_endpoint = f"{self.base_url}/sharing/rest/oauth2/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(token_endpoint, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.expires_in = token_data.get("expires_in")
            
            print("✓ Access token refreshed successfully!")
            return token_data
        else:
            raise Exception(f"Failed to refresh token: {response.text}")
    
    def get_user_info(self):
        """Get information about the authenticated user"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authorize() first.")
        
        user_endpoint = f"{self.base_url}/sharing/rest/community/self"
        
        params = {
            "token": self.access_token,
            "f": "json"
        }
        
        response = requests.get(user_endpoint, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get user info: {response.text}")
    
    def make_authenticated_request(self, url, method="GET", **kwargs):
        """Make an authenticated request to ArcGIS API"""
        if not self.access_token:
            raise Exception("Not authenticated. Call authorize() first.")
        
        # Add token to parameters
        params = kwargs.get("params", {})
        params["token"] = self.access_token
        params["f"] = "json"
        kwargs["params"] = params
        
        # Make request
        response = requests.request(method, url, **kwargs)
        return response.json()

def main():
    """Example usage of the ArcGIS OAuth client"""
    
    # SECURITY WARNING: Never hardcode credentials in production code!
    # Use environment variables or secure configuration management
    
    # Example using environment variables (recommended):
    # client_id = os.getenv("ARCGIS_CLIENT_ID")
    # client_secret = os.getenv("ARCGIS_CLIENT_SECRET")
    
    # For this example, we'll use placeholder values
    # Replace these with your actual credentials (stored securely!)
    client_id = "Bzd4F4tByxJgX2Ea"
    client_secret = "1172253c145e402682360b753af03dfd"
    
    # Initialize the auth client
    auth = ArcGISAuth(client_id, client_secret)
    
    try:
        # Perform OAuth authorization
        auth.authorize()
        
        # Get user information
        user_info = auth.get_user_info()
        print("\n✓ User authenticated successfully!")
        print(f"  Username: {user_info.get('username')}")
        print(f"  Full Name: {user_info.get('fullName')}")
        print(f"  Email: {user_info.get('email')}")
        
        # Example: Search for content
        print("\n📁 Searching for user's content...")
        search_url = f"{auth.base_url}/sharing/rest/search"
        search_results = auth.make_authenticated_request(
            search_url,
            params={
                "q": f"owner:{user_info.get('username')}",
                "num": 5
            }
        )
        
        if search_results.get("results"):
            print(f"Found {search_results.get('total')} items:")
            for item in search_results.get("results", [])[:5]:
                print(f"  - {item.get('title')} ({item.get('type')})")
        
        # Save tokens for later use (optional)
        tokens = {
            "access_token": auth.access_token,
            "refresh_token": auth.refresh_token,
            "expires_in": auth.expires_in
        }
        
        # You could save these tokens securely for future use
        # For example, in an encrypted file or secure storage
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return auth

if __name__ == "__main__":
    print("=" * 50)
    print("ArcGIS OAuth 2.0 Authentication Demo")
    print("=" * 50)
    print("\n⚠️  IMPORTANT: Never share or commit your credentials!")
    print("Store them in environment variables or secure config files.\n")
    
    # Run the example
    auth_client = main()
    
    # Example of using the temporary token you provided
    # NOTE: This is just for demonstration. Never hardcode tokens!
    """
    # If you have an existing token, you can use it directly:
    temporary_token = "YOUR_TEMPORARY_TOKEN"
    
    # Make a request with the temporary token
    response = requests.get(
        "https://www.arcgis.com/sharing/rest/community/self",
        params={
            "token": temporary_token,
            "f": "json"
        }
    )
    
    if response.status_code == 200:
        user_data = response.json()
        print(f"User: {user_data.get('username')}")
    """