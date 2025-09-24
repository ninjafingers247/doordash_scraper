#!/usr/bin/env python3
"""
DoorDash Guest User Flow Automation using curl_cffi
Replicates the exact API sequence: Guest Creation → Address Setup → Content Feed Access
"""

import json
import uuid
import time
import base64
from urllib.parse import quote
from curl_cffi import requests

class DoorDashGuestFlow:
    def __init__(self):
        self.base_url = "https://consumer-mobile-bff.doordash.com"
        self.session = requests.Session(impersonate="chrome110")  # Impersonate Chrome
        self.jwt_token = None
        self.session_id = str(uuid.uuid4()) + "-dd-and"
        self.device_id = str(uuid.uuid4()).replace('-', '')
        self.correlation_id = str(uuid.uuid4()) + "-dd-and"
        self.client_request_id = str(uuid.uuid4()) + "-dd-and"
        self.address_id = None
        self.lat = None
        self.lng = None
        
        # Set more realistic default headers based on real Android app
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
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })
        
        # Update session headers immediately
        self.update_session_headers()
        
    def update_session_headers(self):
        """Update session-specific headers"""
        self.session.headers.update({
            'X-Session-Id': self.session_id,
            'X-Client-Request-Id': self.client_request_id,
            'X-Correlation-Id': self.correlation_id,
            'DD-IDs': json.dumps({
                "dd_device_id": self.device_id,
                "dd_session_id": f"sx_{str(uuid.uuid4())}",
                "dd_android_id": self.device_id,
                "dd_android_advertising_id": str(uuid.uuid4())
            })
        })
        
        if self.jwt_token:
            self.session.headers['Authorization'] = f'JWT {self.jwt_token}'
    
    def generate_sentry_headers(self, transaction=""):
        """Generate Sentry tracing headers"""
        trace_id = str(uuid.uuid4()).replace('-', '')
        span_id = str(uuid.uuid4()).replace('-', '')[:16]
        
        sentry_trace = f"{trace_id}-{span_id}-0"
        baggage_parts = [
            "sentry-environment=production-doordash",
            "sentry-public_key=72ed69f9da5c40b89fd268bdbaa40d07",
            "sentry-release=com.dd.doordash%4015.221.7%2B15221079"
        ]
        
        if transaction:
            baggage_parts.append(f"sentry-transaction={transaction}")
            
        return {
            'Sentry-Trace': sentry_trace,
            'Baggage': ','.join(baggage_parts)
        }
    
    def debug_request_info(self):
        """Debug function to show current headers"""
        print("🔍 Debug: Current headers:")
        for key, value in self.session.headers.items():
            print(f"   {key}: {value}")
        print()
    
    def step_1_health_check(self):
        """Step 1: Health Check"""
        print("🔍 Step 1: Health Check")
        
        # Add small delay to seem more natural
        time.sleep(1)
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        try:
            # Try with a simpler endpoint first
            response = self.session.get(f"{self.base_url}/status_ok", timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 403:
                print("   ⚠️  403 Forbidden - Trying alternative approach...")
                
                # Try without some headers that might trigger blocking
                temp_headers = self.session.headers.copy()
                self.session.headers.pop('Sec-Fetch-Dest', None)
                self.session.headers.pop('Sec-Fetch-Mode', None) 
                self.session.headers.pop('Sec-Fetch-Site', None)
                
                response = self.session.get(f"{self.base_url}/status_ok", timeout=30)
                print(f"   Retry Status: {response.status_code}")
                
                # Restore headers
                self.session.headers.update(temp_headers)
            
            if response.status_code != 200:
                print(f"   Response headers: {dict(list(response.headers.items())[:5])}")
                print(f"   Response body: {response.text[:300]}")
                
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_2_create_guest_user(self):
        """Step 2: Create Guest User"""
        print("👤 Step 2: Create Guest User")
        
        password = str(uuid.uuid4())
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        payload = {
            "password": password
        }
        
        try:
            # Add Content-Type for POST request
            post_headers = {'Content-Type': 'application/json; charset=UTF-8'}
            response = self.session.post(
                f"{self.base_url}/v1/consumer_profile/create_full_guest",
                json=payload,
                headers=post_headers
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Extract JWT token from response - it's in auth_token.token
                if 'auth_token' in data and 'token' in data['auth_token']:
                    self.jwt_token = data['auth_token']['token']
                    print(f"   ✅ JWT Token acquired")
                    self.update_session_headers()
                    return True
                elif 'token' in data:
                    self.jwt_token = data['token']
                    print(f"   ✅ JWT Token acquired (direct)")
                    self.update_session_headers()
                    return True
                else:
                    print("   ❌ No token in response")
                    print(f"   Response keys: {list(data.keys())}")
                    if 'auth_token' in data:
                        print(f"   Auth token keys: {list(data['auth_token'].keys())}")
            
            return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_3_get_experiments(self):
        """Step 3: Get Feature Flags/Experiments"""
        print("🧪 Step 3: Get Feature Flags")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        # Common experiments from the captured data
        experiments = [
            'hide_doubledash_postcheckout',
            'android_cx_nd_address_debug_logging',
            'android_cx_store_carousel_redesign_round_1',
            'android_cx_store_cell_redesign_round_3'
        ]
        
        payload = {
            "experiments": experiments
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/experiments/",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_4_register_device(self):
        """Step 4: Register Device for Push Notifications"""
        print("📱 Step 4: Register Device")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        payload = {
            "notification_token": f"fake_token_{self.device_id}",
            "device_manufacturer": "Google",
            "device_model": "sdk_gphone_x86",
            "device_name": "generic_x86_arm",
            "app_version": "11"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/v1/register_device/",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_5_privacy_consents(self):
        """Step 5: Get Privacy Consents"""
        print("🔒 Step 5: Privacy Consents")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        params = {
            "segment_write_key": "E6UuE4W1vK18KuDgRFO1A87XS89Vuz5j"
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/v1/user/privacy_consents",
                params=params
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_6_get_user_profile(self):
        """Step 6: Get User Profile"""
        print("👥 Step 6: Get User Profile")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        try:
            response = self.session.get(f"{self.base_url}/v2/consumers/me")
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_7_update_language(self):
        """Step 7: Update Language Preference"""
        print("🌐 Step 7: Update Language")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        payload = {
            "language": "en-US"
        }
        
        try:
            response = self.session.patch(
                f"{self.base_url}/v2/consumers/me",
                json=payload
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_8_get_addresses(self):
        """Step 8: Get User Addresses"""
        print("🏠 Step 8: Get Addresses")
        
        headers = self.generate_sentry_headers()
        self.session.headers.update(headers)
        
        try:
            response = self.session.get(f"{self.base_url}/v2/addresses")
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_9_address_autocomplete(self, address_query="New York"):
        """Step 9: Address Autocomplete Search"""
        print(f"🔍 Step 9: Address Autocomplete - '{address_query}'")
        
        headers = self.generate_sentry_headers("AddressActivity")
        self.session.headers.update(headers)
        
        params = {
            "input": address_query,
            "radius": "100"
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
                    place_id = first_address.get('google_place_id')  # Fixed field name
                    print(f"   ✅ Found address suggestions: {len(data)}")
                    if place_id:
                        print(f"   ✅ Using place_id: {place_id}")
                        return place_id
                    else:
                        print(f"   ❌ No google_place_id in first result: {first_address}")
                        return None
                else:
                    print(f"   ❌ No address suggestions found")
                    
            return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def step_10_get_address_details(self, place_id):
        """Step 10: Get Address Details"""
        print("📍 Step 10: Get Address Details")
        
        headers = self.generate_sentry_headers("AddressActivity")
        self.session.headers.update(headers)
        
        params = {
            "place_id": place_id
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/v2/addresses/details",
                params=params
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                # Extract coordinates
                if 'lat' in data and 'lng' in data:
                    self.lat = data['lat']
                    self.lng = data['lng']
                    print(f"   ✅ Coordinates: {self.lat}, {self.lng}")
                    return data
                    
            return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def step_11_validate_address(self, place_id):
        """Step 11: Validate Address"""
        print("✅ Step 11: Validate Address")
        
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
        """Step 12: Add Address to Profile"""
        print("➕ Step 12: Add Address")
        
        headers = self.generate_sentry_headers("AddressActivity")
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
                    return True
                    
            return False
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_13_set_default_address(self):
        """Step 13: Set Default Address"""
        print("🏠 Step 13: Set Default Address")
        
        if not self.address_id:
            print("   ❌ No address ID available")
            return False
        
        headers = self.generate_sentry_headers("AddressActivity")
        self.session.headers.update(headers)
        
        try:
            response = self.session.patch(
                f"{self.base_url}/v1/consumer_profile/address/{self.address_id}/set_default"
            )
            print(f"   Status: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def step_14_homepage_feed(self):
        """Step 14: Get Homepage Feed (Required for Content Feed cursor)"""
        print("🏠 Step 14: Homepage Feed")
        
        if not self.lat or not self.lng:
            print("   ❌ No coordinates available")
            return None
        
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
                # Look for cursor information in the response
                # This is typically embedded in the feed data
                print(f"   ✅ Homepage feed loaded successfully")
                return data
                
            return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def step_15_content_feed(self, cursor_id=None):
        """Step 15: Get Content Feed (TARGET ENDPOINT!)"""
        print("🎯 Step 15: Content Feed (TARGET!)")
        
        if not self.lat or not self.lng:
            print("   ❌ No coordinates available")
            return None
        
        headers = self.generate_sentry_headers("FacetFeedActivity")
        headers.update({
            'X-Facets-Feature-Backend-Driven-Badges': 'true',
            'X-Facets-Feature-Store-Cell-Redesign-Round-3': 'treatmentVariant3'
        })
        self.session.headers.update(headers)
        
        # Check if this is a "Now on DoorDash" cursor that needs special handling
        if cursor_id and isinstance(cursor_id, str) and len(cursor_id) > 100:
            try:
                # Decode to check if it's a valid cursor
                decoded = base64.b64decode(cursor_id).decode()
                cursor_data = json.loads(decoded)
                print(f"   📋 Using v2/feed endpoint with 'Now on DoorDash' cursor")
                print(f"   🔍 Cursor contains content_ids: {cursor_data.get('content_ids', [])}")
                
                # Use the standard v2/feed endpoint with the cursor as id parameter
                params = {
                    "lat": str(self.lat),
                    "lng": str(self.lng),
                    "id": cursor_id
                }
                
                response = self.session.get(f"{self.base_url}/v2/feed/", params=params)
                print(f"   Status: {response.status_code}")
                print(f"   Response Size: {len(response.content)} bytes")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   🎉 SUCCESS! 'Now on DoorDash' Feed accessed!")
                    print(f"   📊 Feed contains {len(data) if isinstance(data, list) else 'complex'} items")
                    return data
                else:
                    print(f"   ❌ Failed to access 'Now on DoorDash' feed")
                    print(f"   Response: {response.text[:200]}...")
                    # Don't return None, fall through to try default approach
                    
            except Exception as e:
                print(f"   ⚠️  Error with 'Now on DoorDash' cursor, falling back to default: {e}")
        
        # Default v2/feed endpoint
        params = {
            "lat": str(self.lat),
            "lng": str(self.lng)
        }
        
        # If we have a cursor from homepage, use it
        if cursor_id:
            params["id"] = cursor_id
        else:
            # Use a default cursor structure based on captured data
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
            
            # Encode cursor as base64
            cursor_json = json.dumps(default_cursor)
            cursor_b64 = base64.b64encode(cursor_json.encode()).decode()
            params["id"] = cursor_b64
        
        try:
            response = self.session.get(
                f"{self.base_url}/v2/feed/",
                params=params
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response Size: {len(response.content)} bytes")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   🎉 SUCCESS! Content Feed accessed!")
                print(f"   📊 Feed contains {len(data) if isinstance(data, list) else 'complex'} items")
                return data
            else:
                print(f"   ❌ Failed to access content feed")
                print(f"   Response: {response.text[:200]}...")
                
            return None
        except Exception as e:
            print(f"   Error: {e}")
            return None
    
    def run_complete_flow(self, address_query="New York, NY"):
        """Run the complete guest user flow"""
        print("🚀 Starting DoorDash Guest User Flow")
        print("=" * 60)
        
        # Stage 1: Initialization
        if not self.step_1_health_check():
            print("❌ Health check failed")
            return False
            
        if not self.step_2_create_guest_user():
            print("❌ Guest user creation failed")
            return False
            
        if not self.step_3_get_experiments():
            print("❌ Experiments fetch failed")
            return False
            
        if not self.step_4_register_device():
            print("❌ Device registration failed")
            return False
        
        # Stage 2: User Setup
        if not self.step_5_privacy_consents():
            print("❌ Privacy consents failed")
            return False
            
        if not self.step_6_get_user_profile():
            print("❌ User profile fetch failed")
            return False
            
        if not self.step_7_update_language():
            print("❌ Language update failed")
            return False
        
        # Stage 3: Address Flow
        if not self.step_8_get_addresses():
            print("❌ Address list fetch failed")
            return False
        
        place_id = self.step_9_address_autocomplete(address_query)
        if not place_id:
            print("❌ Address autocomplete failed")
            return False
        
        address_details = self.step_10_get_address_details(place_id)
        if not address_details:
            print("❌ Address details fetch failed")
            return False
            
        if not self.step_11_validate_address(place_id):
            print("❌ Address validation failed")
            return False
            
        if not self.step_12_add_address(place_id):
            print("❌ Add address failed")
            return False
            
        if not self.step_13_set_default_address():
            print("❌ Set default address failed")
            return False
        
        # Stage 4: Content Access
        homepage_data = self.step_14_homepage_feed()
        if not homepage_data:
            print("❌ Homepage feed failed")
            return False
        
        content_feed_data = self.step_15_content_feed()
        if not content_feed_data:
            print("❌ Content feed access failed")
            return False
        
        print("\n" + "=" * 60)
        print("🎉 COMPLETE SUCCESS!")
        print("✅ Guest user created and authenticated")
        print("✅ Address added and validated")
        print("✅ Content Feed accessed successfully!")
        print("=" * 60)
        
        return True

def main():
    """Main execution function"""
    print("DoorDash Guest Flow Automation")
    print("Using curl_cffi for HTTP requests")
    print()
    
    # Initialize the flow
    flow = DoorDashGuestFlow()
    
    # Run the complete flow
    success = flow.run_complete_flow("New York, NY")
    
    if success:
        print("\n🎯 Flow completed successfully!")
        print("You can now access the DoorDash Content Feed as a guest user.")
    else:
        print("\n❌ Flow failed at some point.")
        print("Check the error messages above for details.")

if __name__ == "__main__":
    main()

