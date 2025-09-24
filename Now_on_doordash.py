


#!/usr/bin/env python3
"""
Optimized DoorDash "Now on DoorDash" Section Extractor
Only includes necessary steps for accessing store data efficiently
"""

import json
import uuid
import time
import base64
from urllib.parse import quote

try:
    import requests
    from curl_cffi import requests
except ImportError:
    print("❌ Missing curl_cffi dependency!")
    print("Install with: pip install curl_cffi")
    exit(1)


class OptimizedDoorDashFlow:
    def __init__(self):
        self.base_url = "https://consumer-mobile-bff.doordash.com"
        self.session = requests.Session(impersonate="chrome110")
        self.jwt_token = None
        self.session_id = str(uuid.uuid4()) + "-dd-and"
        self.device_id = str(uuid.uuid4()).replace('-', '')
        self.correlation_id = str(uuid.uuid4()) + "-dd-and"
        self.client_request_id = str(uuid.uuid4()) + "-dd-and"
        self.address_id = None
        self.lat = None
        self.lng = None
        
        # Realistic mobile app headers
        self.session.headers.update({
            'User-Agent': 'DoorDashConsumer/15.221.7 (Android 11; Google sdk_gphone_x86)',
            'Accept': 'application/json',
            'Accept-Language': 'en-US',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Experience-Id': 'doordash',
            'Client-Version': 'android v15.221.7 b15221079',
            'X-Support-Partner-Dashpass': 'true',
            'DD-User-Locale': 'en-US',
            'X-BFF-Error-Format': 'v2',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        self.update_session_headers()
    
    def update_session_headers(self):
        """Update session with dynamic headers"""
        headers = {
            'X-Session-Id': self.session_id,
            'X-Device-Id': self.device_id,
            'X-Correlation-Id': self.correlation_id,
            'X-Client-Request-Id': self.client_request_id
        }
        
        if self.jwt_token:
            headers['Authorization'] = f'JWT {self.jwt_token}'
        
        self.session.headers.update(headers)
    
    def generate_sentry_headers(self, activity_name="MainActivity"):
        """Generate dynamic Sentry headers"""
        trace_id = str(uuid.uuid4()).replace('-', '')
        span_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        return {
            'Sentry-Trace': f'{trace_id}-{span_id}-1',
            'Baggage': f'sentry-environment=production,sentry-release=android-15.221.7,sentry-transaction={activity_name}'
        }
    
    def step_1_health_check(self):
        """Optional: Health Check"""
        print("🏥 Step 1: Health Check")
        try:
            response = self.session.get(f"{self.base_url}/status_ok")
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Warning: {e}")
            return True  # Continue even if health check fails
    
    def step_2_create_guest(self):
        """CRITICAL: Create Guest User & Get JWT Token"""
        print("👤 Step 2: Create Guest User (CRITICAL)")
        
        headers = self.generate_sentry_headers("CreateGuestActivity")
        headers.update({
            'Content-Type': 'application/json; charset=UTF-8'
        })
        self.session.headers.update(headers)
        
        payload = {
            "password": str(uuid.uuid4())[:8] + "A1!"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/consumer_profile/create_full_guest",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'auth_token' in data and 'token' in data['auth_token']:
                    self.jwt_token = data['auth_token']['token']
                    self.update_session_headers()
                    print("   ✅ JWT Token obtained!")
                    return True
                else:
                    print("   ❌ No token in response")
                    return False
            else:
                print(f"   ❌ Failed: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_8_get_addresses(self):
        """Step 8: Get User Addresses (check only)"""
        print("📍 Step 8: Get Addresses")
        
        if not self.jwt_token:
            print("   ❌ No JWT token")
            return False
        
        headers = self.generate_sentry_headers("AddressActivity")
        self.session.headers.update(headers)
        
        try:
            response = self.session.get(f"{self.base_url}/v2/addresses")
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_9_address_autocomplete(self, address_query):
        """Get address suggestions"""
        print(f"🔍 Step 9: Address Autocomplete for '{address_query}'")
        
        if not self.jwt_token:
            print("   ❌ No JWT token")
            return None
        
        headers = self.generate_sentry_headers("AddressAutocompleteActivity")
        self.session.headers.update(headers)
        
        params = {
            'input': address_query,
            'radius': '100'
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/v1/addresses/autocomplete",
                params=params
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data and len(data) > 0:
                    # Get the first address suggestion
                    first_address = data[0]
                    place_id = first_address.get('google_place_id')
                    print(f"   ✅ Found address suggestions: {len(data)}")
                    if place_id:
                        print(f"   ✅ Using place_id: {place_id}")
                        print(f"   📍 Address: {first_address.get('printable_address', 'N/A')}")
                        return place_id
                    else:
                        print(f"   ❌ No google_place_id in first result: {first_address}")
                        return None
                else:
                    print("   ❌ No address suggestions found")
                    return None
            else:
                print(f"   ❌ Autocomplete failed: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def step_10_address_details(self, place_id):
        """Get detailed address info including coordinates"""
        print("📍 Step 10: Get Address Details & Coordinates")
        
        if not self.jwt_token:
            print("   ❌ No JWT token")
            return False
        
        headers = self.generate_sentry_headers("AddressDetailsActivity")
        self.session.headers.update(headers)
        
        params = {
            'place_id': place_id
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/v2/addresses/details",
                params=params
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.lat = data.get('lat')
                self.lng = data.get('lng')
                print(f"   ✅ Coordinates: {self.lat}, {self.lng}")
                print(f"   📍 Address: {data.get('printable_address')}")
                
                # Verify coordinates are valid
                if self.lat is None or self.lng is None:
                    print(f"   ❌ Invalid coordinates in response: {data}")
                    return False
                
                return True
            else:
                print(f"   ❌ Failed to get details: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_11_validate_address(self, place_id):
        """Step 11: Validate Address"""
        print("✅ Step 11: Validate Address")
        
        if not self.jwt_token:
            print("   ❌ No JWT token")
            return False
        
        headers = self.generate_sentry_headers("AddressActivity")
        self.session.headers.update(headers)
        
        payload = {
            "consumer_id": "1125900377027641",  # Dummy consumer ID
            "address_id": "",
            "cart_id": "",
            "google_place_id": place_id
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v2/addresses/validate",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_12_add_address(self, place_id):
        """Add address to user profile"""
        print("➕ Step 12: Add Address to Profile")
        
        if not self.jwt_token:
            print("   ❌ No JWT token")
            return False
        
        headers = self.generate_sentry_headers("AddAddressActivity")
        headers.update({
            'Content-Type': 'application/json; charset=UTF-8'
        })
        self.session.headers.update(headers)
        
        payload = {
            "subpremise": "",
            "dasher_instructions": "",
            "validate_address": False,
            "dropoff_preferences": [
                {"option_id": "1", "instructions": "", "is_default": False},
                {"option_id": "2", "instructions": "", "is_default": True}
            ],
            "google_place_id": place_id,
            "address_link_type": "ADDRESS_LINK_TYPE_UNSPECIFIED"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/consumer_profile/address/",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'id' in data:
                    self.address_id = data['id']
                    print(f"   ✅ Address ID: {self.address_id}")
                    print(f"   📍 Address: {data.get('printable_address', 'N/A')}")
                    return True
                else:
                    print(f"   ❌ No address ID in response: {data}")
                    return False
            else:
                print(f"   ❌ Failed to add address: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_13_set_default_address(self):
        """Set address as default"""
        print("🏠 Step 13: Set Default Address")
        
        if not self.jwt_token or not self.address_id:
            print("   ❌ Missing JWT token or address ID")
            return False
        
        headers = self.generate_sentry_headers("SetDefaultAddressActivity")
        self.session.headers.update(headers)
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/consumer_profile/address/{self.address_id}/set_default"
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Address set as default!")
                return True
            elif response.status_code == 404:
                print(f"   ⚠️  Address not found (404) - might already be set or invalid ID")
                print(f"   🔄 Continuing anyway as we have coordinates...")
                return True  # Continue the flow since we have coordinates
            else:
                print(f"   ❌ Failed to set default: {response.text[:200]}")
                # Don't abort here, we might still be able to continue
                return True
        except Exception as e:
            print(f"   Error: {e}")
            return True  # Continue anyway
    
    def step_14_homepage_feed(self):
        """Get homepage feed with sections"""
        print("🏠 Step 14: Homepage Feed")
        
        if not self.lat or not self.lng:
            print("   ❌ No coordinates available")
            return None
        
        print(f"   📍 Using coordinates: {self.lat}, {self.lng}")
        
        headers = self.generate_sentry_headers("PlanEnrollmentActivity")
        # Add facets headers for homepage
        headers.update({
            'X-Facets-Feature-Item-Carousel': 'true',
            'X-Facets-Feature-Backend-Driven-Badges': 'true',
            'X-Facets-Feature-No-Tile': 'true',
            'X-Facets-Version': '4.0.0',
            'X-Facets-Feature-Item-Steppers': 'true',
            'X-Facets-Feature-Quick-Add-Stepper-Variant': 'true',
            'X-Facets-Feature-Store-Carousel-Redesign-Round-1': 'treatmentVariant2',
            'X-Facets-Feature-Store-Cell-Redesign-Round-3': 'treatmentVariant3',
            'X-Gifting-Intent': 'false'
        })
        self.session.headers.update(headers)
        
        params = {
            "lat": str(self.lat),
            "lng": str(self.lng)
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/v3/feed/homepage",
                params=params
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response Size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ Homepage feed obtained!")
                return data
            else:
                print(f"   ❌ Failed: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def step_15_content_feed(self, cursor_id=None):
        """Get content feed with stores"""
        print("🎯 Step 15: Content Feed")
        
        if not self.lat or not self.lng:
            print("   ❌ No coordinates available")
            return None
        
        headers = self.generate_sentry_headers("FacetFeedActivity")
        headers.update({
            'X-Facets-Feature-Backend-Driven-Badges': 'true',
            'X-Facets-Feature-Store-Cell-Redesign-Round-3': 'treatmentVariant3'
        })
        self.session.headers.update(headers)
        
        params = {
            "lat": str(self.lat),
            "lng": str(self.lng)
        }
        
        # Use provided cursor or create default one
        if cursor_id:
            params["id"] = cursor_id
            print(f"   🎯 Using provided cursor")
        else:
            # Default cursor for general content
            default_cursor = {
                "offset": 0,
                "content_ids": ["10821511", "27460306", "33917167"],
                "request_parent_id": "DEFAULT_HOMEPAGE",
                "request_child_id": "carousel.standard:store_carousel:eta",
                "cross_vertical_page_type": "DEFAULT_HOMEPAGE",
                "page_stack_trace": [],
                "vertical_ids": [],
                "baseCursor": {
                    "page_id": "eta",
                    "page_type": "STORE_CAROUSEL_LANDING",
                    "cursor_version": "FACET"
                }
            }
            cursor_json = json.dumps(default_cursor)
            cursor_b64 = base64.b64encode(cursor_json.encode()).decode()
            params["id"] = cursor_b64
            print(f"   🎯 Using default cursor")
        
        try:
            response = self.session.get(
                f"{self.base_url}/v2/feed/",
                params=params
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response Size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ Content feed obtained!")
                return data
            else:
                print(f"   ❌ Failed: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"   Error: {e}")
            return None


def find_now_on_doordash_cursor(homepage_data):
    """Find the 'Now on DoorDash' section cursor"""
    print("🔍 Searching for 'Now on DoorDash' section...")
    
    def search_for_now_on_doordash(item, path=""):
        """Recursively search for 'Now on DoorDash' section"""
        if isinstance(item, dict):
            # Check if this item has text with "Now on DoorDash" title
            if 'text' in item and isinstance(item['text'], dict):
                title = item['text'].get('title', '').strip()
                if title and 'now on doordash' in title.lower():
                    print(f"   🎯 Found section: '{title}' at path: {path}")
                    
                    # Look for cursor in events
                    if 'events' in item and 'click' in item['events']:
                        click_data = item['events']['click'].get('data', {})
                        if 'uri' in click_data:
                            uri = click_data['uri']
                            print(f"   📍 URI: {uri}")
                            
                            # Extract cursor from facet_feed/ URI
                            if uri.startswith('facet_feed/'):
                                cursor = uri[11:]  # Remove 'facet_feed/' prefix
                                if cursor.endswith('/'):
                                    cursor = cursor[:-1]  # Remove trailing slash
                                print(f"   ✅ Extracted cursor for 'Now on DoorDash'!")
                                return cursor
            
            # Recursively search in nested items
            for key, value in item.items():
                if isinstance(value, (dict, list)):
                    result = search_for_now_on_doordash(value, f"{path}.{key}")
                    if result:
                        return result
        
        elif isinstance(item, list):
            for i, sub_item in enumerate(item):
                result = search_for_now_on_doordash(sub_item, f"{path}[{i}]")
                if result:
                    return result
        
        return None
    
    cursor = search_for_now_on_doordash(homepage_data)
    if cursor:
        print("   🎉 'Now on DoorDash' cursor found!")
        return cursor
    else:
        print("   ❌ 'Now on DoorDash' section not found in this location")
        return None


def extract_stores_from_feed(feed_data, source_name="feed"):
    """Extract store information from feed data"""
    print(f"📦 Extracting stores from {source_name}...")
    
    stores = []
    
    def extract_store_info(item, path=""):
        """Recursively extract store information"""
        if isinstance(item, dict):
            store_info = {}
            
            # Extract basic info
            if 'text' in item and isinstance(item['text'], dict):
                text_data = item['text']
                store_info['name'] = text_data.get('title', '').strip()
                store_info['subtitle'] = text_data.get('subtitle', '').strip()
            
            # Extract custom data (ratings, etc.)
            if 'custom' in item and isinstance(item['custom'], dict):
                custom_data = item['custom']
                store_info['rating'] = custom_data.get('rating')
                store_info['delivery_fee'] = custom_data.get('delivery_fee')
                store_info['delivery_time'] = custom_data.get('delivery_time')
            
            # Extract store ID and other identifiers
            if 'events' in item and 'click' in item['events']:
                click_data = item['events']['click'].get('data', {})
                store_info['store_id'] = click_data.get('store_id')
                store_info['uri'] = click_data.get('uri')
            
            # If we have a store name, this is likely a store
            if store_info.get('name') and len(store_info.get('name', '')) > 2:
                store_info['source'] = source_name
                store_info['path'] = path
                stores.append(store_info)
            
            # Recursively search nested items
            for key, value in item.items():
                if isinstance(value, (dict, list)):
                    extract_store_info(value, f"{path}.{key}")
        
        elif isinstance(item, list):
            for i, sub_item in enumerate(item):
                extract_store_info(sub_item, f"{path}[{i}]")
    
    extract_store_info(feed_data)
    
    # Remove duplicates based on name
    unique_stores = []
    seen_names = set()
    for store in stores:
        name = store.get('name', '').lower()
        if name and name not in seen_names:
            seen_names.add(name)
            unique_stores.append(store)
    
    print(f"   📊 Found {len(unique_stores)} unique stores")
    return unique_stores


def run_optimized_flow(address_query="Elms Bup 10439"):
    """Run the optimized flow to get 'Now on DoorDash' stores"""
    print("🚀 Starting Optimized DoorDash Flow")
    print("=" * 60)
    
    flow = OptimizedDoorDashFlow()
    
    # Step 1: Optional health check
    flow.step_1_health_check()
    
    # Step 2: CRITICAL - Create guest user
    if not flow.step_2_create_guest():
        print("❌ Failed to create guest user - ABORTING")
        return None
    
    # Step 8: Check addresses endpoint
    if not flow.step_8_get_addresses():
        print("❌ Address check failed - ABORTING")
        return None
    
    # Step 9: Address autocomplete
    place_id = flow.step_9_address_autocomplete(address_query)
    if not place_id:
        print("❌ Address autocomplete failed - ABORTING")
        return None
    
    # Step 10: Get address details and coordinates
    if not flow.step_10_address_details(place_id):
        print("❌ Failed to get address details - ABORTING")
        return None
    
    # Step 11: Validate address
    if not flow.step_11_validate_address(place_id):
        print("❌ Address validation failed - ABORTING")
        return None
    
    # Step 12: Add address to profile
    if not flow.step_12_add_address(place_id):
        print("❌ Failed to add address - ABORTING")
        return None
    
    # Step 13: Set as default address
    if not flow.step_13_set_default_address():
        print("❌ Failed to set default address - continuing anyway")
        # Don't abort here, continue with the flow
    
    # Step 14: Get homepage feed
    homepage_data = flow.step_14_homepage_feed()
    if not homepage_data:
        print("❌ Failed to get homepage feed - ABORTING")
        return None
    
    # Save homepage data for analysis
    with open('homepage_feed.json', 'w', encoding='utf-8') as f:
        json.dump(homepage_data, f, indent=2)
    print("💾 Homepage feed saved to homepage_feed.json")
    
    # Find 'Now on DoorDash' section
    now_cursor = find_now_on_doordash_cursor(homepage_data)
    
    if now_cursor:
        # Step 15: Get 'Now on DoorDash' content feed
        print("\n🎯 Getting 'Now on DoorDash' content...")
        now_feed_data = flow.step_15_content_feed(now_cursor)
        
        if now_feed_data:
            # Save the specific feed data
            with open('now_on_doordash_feed.json', 'w', encoding='utf-8') as f:
                json.dump(now_feed_data, f, indent=2)
            print("💾 'Now on DoorDash' feed saved to now_on_doordash_feed.json")
            
            # Extract stores
            stores = extract_stores_from_feed(now_feed_data, "Now on DoorDash")
            
            if stores:
                # Save stores data
                with open('now_on_doordash_stores.json', 'w', encoding='utf-8') as f:
                    json.dump(stores, f, indent=2)
                print(f"💾 {len(stores)} stores saved to now_on_doordash_stores.json")
                
                # Display summary
                print("\n" + "=" * 60)
                print("🎉 SUCCESS! 'Now on DoorDash' Stores Found:")
                print("=" * 60)
                for i, store in enumerate(stores[:10], 1):  # Show first 10
                    name = store.get('name', 'Unknown')
                    rating = store.get('rating', 'N/A')
                    delivery_time = store.get('delivery_time', 'N/A')
                    print(f"   {i:2d}. {name} (⭐ {rating}) - {delivery_time}")
                
                if len(stores) > 10:
                    print(f"   ... and {len(stores) - 10} more stores")
                print("=" * 60)
                
                return stores
            else:
                print("❌ No stores found in 'Now on DoorDash' feed")
                return None
        else:
            print("❌ Failed to get 'Now on DoorDash' content feed")
            return None
    else:
        print("❌ 'Now on DoorDash' section not found")
        print("💡 This might be location-dependent or time-dependent")
        
        # Fallback: Get general content feed
        print("\n🔄 Fallback: Getting general content feed...")
        general_feed = flow.step_15_content_feed()
        
        if general_feed:
            with open('general_content_feed.json', 'w', encoding='utf-8') as f:
                json.dump(general_feed, f, indent=2)
            print("💾 General content feed saved to general_content_feed.json")
            
            stores = extract_stores_from_feed(general_feed, "General Feed")
            if stores:
                with open('general_stores.json', 'w', encoding='utf-8') as f:
                    json.dump(stores, f, indent=2)
                print(f"💾 {len(stores)} general stores saved to general_stores.json")
                return stores
        
        return None


if __name__ == "__main__":
    print("🎯 Optimized DoorDash 'Now on DoorDash' Extractor")
    print("📍 Testing with: Elms Bup 10439")
    print()
    
    stores = run_optimized_flow("Elms Bup 10439")
    
    if stores:
        print(f"\n✅ Successfully extracted {len(stores)} stores!")
    else:
        print("\n❌ Failed to extract stores")
