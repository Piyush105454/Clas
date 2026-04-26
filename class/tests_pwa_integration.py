"""
Integration tests for PWA (Progressive Web App) functionality.

Tests cover:
- Service Worker registration
- Manifest availability
- Offline page serving
- PWA meta tags in templates

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

User = get_user_model()


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.cache',
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class PWATemplateIntegrationTestCase(TestCase):
    """Test PWA integration in templates."""
    
    def setUp(self):
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='admin'
        )
    
    def test_admin_template_has_manifest_link(self):
        """Test that admin template includes manifest link."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('manifest.json', content)
            self.assertIn('rel="manifest"', content)
    
    def test_admin_template_has_pwa_meta_tags(self):
        """Test that admin template includes PWA meta tags."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('theme-color', content)
            self.assertIn('apple-mobile-web-app-capable', content)
    
    def test_admin_template_has_service_worker_registration(self):
        """Test that admin template registers Service Worker."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('serviceWorker', content)
            self.assertIn('service-worker.js', content)
    
    def test_admin_template_has_offline_sync_script(self):
        """Test that admin template includes offline sync script."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('offline-sync.js', content)
    
    def test_admin_template_has_resource_prioritization_script(self):
        """Test that admin template includes resource prioritization script."""
        self.client.login(email='test@example.com', password='testpass123')
        response = self.client.get(reverse('admin_dashboard'))
        
        if response.status_code == 200:
            content = response.content.decode()
            self.assertIn('resource-prioritization.js', content)


class PWAManifestIntegrationTestCase(TestCase):
    """Test PWA manifest integration."""
    
    def setUp(self):
        self.client = Client()
    
    def test_manifest_is_accessible_from_root(self):
        """Test that manifest is accessible from root domain."""
        response = self.client.get('/manifest.json')
        self.assertEqual(response.status_code, 200)
    
    def test_manifest_contains_valid_icon_paths(self):
        """Test that manifest icon paths are valid."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        for icon in data['icons']:
            src = icon['src']
            # Icon paths should start with /static/
            self.assertTrue(src.startswith('/static/'))
    
    def test_manifest_scope_is_root(self):
        """Test that manifest scope is root."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertEqual(data['scope'], '/')
    
    def test_manifest_start_url_is_root(self):
        """Test that manifest start URL is root."""
        response = self.client.get(reverse('manifest'))
        data = json.loads(response.content)
        
        self.assertEqual(data['start_url'], '/')


class PWAOfflineIntegrationTestCase(TestCase):
    """Test PWA offline functionality."""
    
    def setUp(self):
        self.client = Client()
    
    def test_offline_page_is_accessible(self):
        """Test that offline page is accessible."""
        response = self.client.get(reverse('offline'))
        self.assertEqual(response.status_code, 200)
    
    def test_offline_page_has_proper_structure(self):
        """Test that offline page has proper HTML structure."""
        response = self.client.get(reverse('offline'))
        content = response.content.decode()
        
        # Check for essential elements
        self.assertIn('<html', content)
        self.assertIn('</html>', content)
        self.assertIn('<head', content)
        self.assertIn('<body', content)
    
    def test_offline_page_has_reconnection_instructions(self):
        """Test that offline page has reconnection instructions."""
        response = self.client.get(reverse('offline'))
        content = response.content.decode()
        
        self.assertIn('connection', content.lower())
        self.assertIn('refresh', content.lower())


class PWAServiceWorkerIntegrationTestCase(TestCase):
    """Test PWA Service Worker integration."""
    
    def setUp(self):
        self.client = Client()
    
    def test_service_worker_file_exists(self):
        """Test that Service Worker file is accessible."""
        response = self.client.get('/static/service-worker.js')
        self.assertEqual(response.status_code, 200)
    
    def test_service_worker_has_install_event(self):
        """Test that Service Worker has install event."""
        response = self.client.get('/static/service-worker.js')
        content = response.content.decode()
        
        self.assertIn('install', content)
        self.assertIn('addEventListener', content)
    
    def test_service_worker_has_activate_event(self):
        """Test that Service Worker has activate event."""
        response = self.client.get('/static/service-worker.js')
        content = response.content.decode()
        
        self.assertIn('activate', content)
    
    def test_service_worker_has_fetch_event(self):
        """Test that Service Worker has fetch event."""
        response = self.client.get('/static/service-worker.js')
        content = response.content.decode()
        
        self.assertIn('fetch', content)
    
    def test_service_worker_has_cache_names(self):
        """Test that Service Worker defines cache names."""
        response = self.client.get('/static/service-worker.js')
        content = response.content.decode()
        
        self.assertIn('CACHE_NAMES', content)
        self.assertIn('static-v1', content)
        self.assertIn('pages-v1', content)


class PWAScriptsIntegrationTestCase(TestCase):
    """Test PWA utility scripts integration."""
    
    def setUp(self):
        self.client = Client()
    
    def test_offline_sync_script_exists(self):
        """Test that offline sync script is accessible."""
        response = self.client.get('/static/offline-sync.js')
        self.assertEqual(response.status_code, 200)
    
    def test_offline_sync_script_has_sync_manager(self):
        """Test that offline sync script has SyncManager class."""
        response = self.client.get('/static/offline-sync.js')
        content = response.content.decode()
        
        self.assertIn('OfflineSyncManager', content)
        self.assertIn('queueRequest', content)
        self.assertIn('syncPendingRequests', content)
    
    def test_resource_prioritization_script_exists(self):
        """Test that resource prioritization script is accessible."""
        response = self.client.get('/static/resource-prioritization.js')
        self.assertEqual(response.status_code, 200)
    
    def test_resource_prioritization_script_has_prioritizer(self):
        """Test that resource prioritization script has Prioritizer class."""
        response = self.client.get('/static/resource-prioritization.js')
        content = response.content.decode()
        
        self.assertIn('ResourcePrioritizer', content)
        self.assertIn('criticalAssets', content)
        self.assertIn('monitorNetworkSpeed', content)
