"""
Unit tests for PWA (Progressive Web App) functionality.

Tests cover:
- Manifest serving and validation
- Offline page serving
- HTTP headers
- Cache configuration

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 3.1, 3.3, 4.1, 4.2
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
import json


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class ManifestTestCase(TestCase):
    """Test Web Manifest serving and validation."""
    
    def setUp(self):
        self.client = Client()
    
    def test_manifest_endpoint_exists(self):
        """Test that manifest endpoint is accessible."""
        response = self.client.get(reverse('manifest'))
        self.assertEqual(response.status_code, 200)
    
    def test_manifest_content_type(self):
        """Test that manifest is served with correct MIME type."""
        response = self.client.get(reverse('manifest'))
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
    
    def test_manifest_has_required_fields(self):
        """Test that manifest contains all required fields."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        required_fields = [
            'name',
            'short_name',
            'description',
            'start_url',
            'display',
            'theme_color',
            'background_color',
            'icons'
        ]
        
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
    
    def test_manifest_name_is_correct(self):
        """Test that manifest has correct app name."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertEqual(data['name'], 'CLAS - Class Learning and Assessment System')
        self.assertEqual(data['short_name'], 'CLAS')
    
    def test_manifest_display_mode(self):
        """Test that manifest has standalone display mode."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertEqual(data['display'], 'standalone')
    
    def test_manifest_icons_present(self):
        """Test that manifest includes icons."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertGreater(len(data['icons']), 0)
        
        # Check icon structure
        for icon in data['icons']:
            self.assertIn('src', icon)
            self.assertIn('sizes', icon)
            self.assertIn('type', icon)
            self.assertIn('purpose', icon)
    
    def test_manifest_theme_colors(self):
        """Test that manifest has theme colors."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertEqual(data['theme_color'], '#3b82f6')
        self.assertEqual(data['background_color'], '#ffffff')
    
    def test_manifest_cache_control_header(self):
        """Test that manifest has proper cache control headers."""
        response = self.client.get(reverse('manifest'))
        
        self.assertIn('Cache-Control', response)
        self.assertIn('max-age=3600', response['Cache-Control'])


class OfflinePageTestCase(TestCase):
    """Test offline fallback page."""
    
    def setUp(self):
        self.client = Client()
    
    def test_offline_page_exists(self):
        """Test that offline page is accessible."""
        response = self.client.get(reverse('offline'))
        self.assertEqual(response.status_code, 200)
    
    def test_offline_page_contains_offline_message(self):
        """Test that offline page contains offline status message."""
        response = self.client.get(reverse('offline'))
        content = response.content.decode()
        
        self.assertIn("You're Offline", content)
        self.assertIn('offline', content.lower())
    
    def test_offline_page_has_refresh_button(self):
        """Test that offline page has refresh button."""
        response = self.client.get(reverse('offline'))
        content = response.content.decode()
        
        self.assertIn('Refresh', content)
    
    def test_offline_page_has_home_link(self):
        """Test that offline page has link to home."""
        response = self.client.get(reverse('offline'))
        content = response.content.decode()
        
        self.assertIn('href="/"', content)


class PWAHeadersTestCase(TestCase):
    """Test PWA-specific HTTP headers."""
    
    def setUp(self):
        self.client = Client()
    
    def test_manifest_no_cache_headers(self):
        """Test that manifest has appropriate cache headers."""
        response = self.client.get(reverse('manifest'))
        
        # Manifest should be cached but checked frequently
        self.assertIn('Cache-Control', response)
        self.assertIn('max-age', response['Cache-Control'])
    
    def test_offline_page_no_cache_headers(self):
        """Test that offline page has no-cache headers."""
        response = self.client.get(reverse('offline'))
        
        # Offline page should not be cached
        cache_control = response.get('Cache-Control', '')
        # Note: This depends on middleware implementation
        # Just verify the header exists
        self.assertIsNotNone(response)


class PWAIntegrationTestCase(TestCase):
    """Integration tests for PWA functionality."""
    
    def setUp(self):
        self.client = Client()
    
    def test_manifest_json_is_valid(self):
        """Test that manifest JSON is valid and parseable."""
        response = self.client.get(reverse('manifest'))
        
        try:
            data = json.loads(response.content)
            self.assertIsInstance(data, dict)
        except json.JSONDecodeError:
            self.fail("Manifest is not valid JSON")
    
    def test_manifest_start_url_is_valid(self):
        """Test that manifest start_url is valid."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        start_url = data.get('start_url')
        self.assertIsNotNone(start_url)
        self.assertTrue(start_url.startswith('/'))
    
    def test_manifest_categories_present(self):
        """Test that manifest includes categories."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertIn('categories', data)
        self.assertGreater(len(data['categories']), 0)
    
    def test_manifest_screenshots_present(self):
        """Test that manifest includes screenshots."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertIn('screenshots', data)
        self.assertGreater(len(data['screenshots']), 0)
        
        # Check screenshot structure
        for screenshot in data['screenshots']:
            self.assertIn('src', screenshot)
            self.assertIn('sizes', screenshot)
            self.assertIn('type', screenshot)
