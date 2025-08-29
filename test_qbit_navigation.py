#!/usr/bin/env python3
"""
qBittorrent Directory Browsing API Test
=======================================

A standalone test script to validate that we can successfully navigate 
directories using qBittorrent's app_get_directory_content() API before 
implementing the full migration.

This test will:
1. Connect to qBittorrent
2. Browse the root directory
3. Navigate to subdirectories
4. Test edge cases (non-existent paths)
5. Compare with any existing Docker path mappings

Usage:
    python test_qbit_navigation.py
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import qbittorrentapi
    from qbittorrentapi import exceptions as qba_exc
except ImportError:
    print("❌ qbittorrent-api not installed. Install with: pip install qbittorrent-api")
    sys.exit(1)

# Try to import our existing configuration
try:
    from src.core.config_manager import ConfigManager
    from src.utils.credential_manager import CredentialManager
    from src.utils.docker_path_mapper import DockerPathMapper
    HAS_CONFIG = True
except ImportError:
    print("⚠️  Could not import project modules. Will use manual configuration.")
    HAS_CONFIG = False


class QBitNavigationTester:
    """Test qBittorrent directory navigation capabilities"""
    
    def __init__(self):
        self.client: Optional[qbittorrentapi.Client] = None
        self.test_results: List[Dict[str, Any]] = []
        self.docker_mapper: Optional[DockerPathMapper] = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", data: Any = None):
        """Log a test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {details}")
        
        if data and isinstance(data, (list, dict)):
            print(f"   📊 Data: {json.dumps(data, indent=2)[:200]}{'...' if len(str(data)) > 200 else ''}")
    
    def connect_to_qbittorrent(self) -> bool:
        """Test qBittorrent connection"""
        print("\n🔌 Testing qBittorrent Connection")
        print("=" * 50)
        
        # Try to get connection details from our config
        if HAS_CONFIG:
            try:
                config_manager = ConfigManager()
                config = config_manager.get_config()
                credential_manager = CredentialManager()
                
                qbit_config = config.qbittorrent
                
                # Resolve credentials
                username = credential_manager.get_credential('QBIT_USERNAME')
                password = credential_manager.get_credential('QBIT_PASSWORD')
                
                if not username or not password:
                    raise Exception("Credentials not found in credential manager")
                
                # Build connection URL
                scheme = 'https' if getattr(qbit_config, 'use_https', False) else 'http'
                base_path = getattr(qbit_config, 'base_path', '') or ''
                qbit_url = f"{scheme}://{qbit_config.host}:{qbit_config.port}{base_path}"
                
                print(f"📡 Using config: {qbit_url} (user: {username})")
                
                # Set up Docker path mapper for comparison
                docker_mapping = getattr(qbit_config, 'docker_path_mapping', {}) or {}
                if docker_mapping:
                    self.docker_mapper = DockerPathMapper(docker_mapping)
                    print(f"🐳 Docker mappings loaded: {docker_mapping}")
                
            except Exception as e:
                print(f"⚠️  Could not load config: {e}")
                print("📝 Please provide connection details manually:")
                qbit_url = input("qBittorrent URL (e.g., http://localhost:8080): ").strip()
                username = input("Username: ").strip()
                password = input("Password: ").strip()
        else:
            print("📝 Please provide qBittorrent connection details:")
            qbit_url = input("qBittorrent URL (e.g., http://localhost:8080): ").strip()
            username = input("Username: ").strip()
            password = input("Password: ").strip()
        
        try:
            # Create qBittorrent client
            self.client = qbittorrentapi.Client(
                host=qbit_url,
                username=username,
                password=password,
                VERIFY_WEBUI_CERTIFICATE=False,  # For testing
                REQUESTS_ARGS={"timeout": (5, 10)},
                DISABLE_LOGGING_DEBUG_OUTPUT=True
            )
            
            # Test authentication
            self.client.auth_log_in()
            version = self.client.app.version
            api_version = self.client.app.web_api_version
            
            self.log_test(
                "qBittorrent Connection", 
                True, 
                f"Connected to qBittorrent {version} (API {api_version})",
                {"version": version, "api_version": api_version, "url": qbit_url}
            )
            
            return True
            
        except Exception as e:
            self.log_test("qBittorrent Connection", False, f"Connection failed: {e}")
            return False
    
    def test_directory_browsing(self):
        """Test basic directory browsing functionality"""
        print("\n📁 Testing Directory Browsing")
        print("=" * 50)
        
        if not self.client:
            self.log_test("Directory Browsing", False, "No qBittorrent client available")
            return []
        
        # Test 1: Browse root directory
        try:
            contents = self.client.app_get_directory_content("/")
            entries = [str(item) for item in contents]
            
            self.log_test(
                "Browse Root Directory", 
                True, 
                f"Found {len(entries)} entries in root",
                {"path": "/", "entries": entries[:10]}  # Limit output
            )
            
        except qba_exc.NotFound404Error:
            self.log_test("Browse Root Directory", False, "Root directory not accessible")
            return []
        except Exception as e:
            self.log_test("Browse Root Directory", False, f"Error: {e}")
            return []
        
        # Test 2: Browse common directories
        common_paths = ["/data", "/downloads", "/media", "/mnt", "/home", "/tmp"]
        accessible_paths = []
        
        for path in common_paths:
            try:
                contents = self.client.app_get_directory_content(path)
                entries = [str(item) for item in contents]
                accessible_paths.append(path)
                
                self.log_test(
                    f"Browse {path}", 
                    True, 
                    f"Found {len(entries)} entries",
                    {"path": path, "entry_count": len(entries), "sample_entries": entries[:5]}
                )
                
            except qba_exc.NotFound404Error:
                self.log_test(f"Browse {path}", True, "Path not accessible (expected for some paths)")
            except Exception as e:
                self.log_test(f"Browse {path}", False, f"Unexpected error: {e}")
        
        return accessible_paths
    
    def test_nested_navigation(self, accessible_paths: List[str]):
        """Test navigating into subdirectories"""
        print("\n🗂️  Testing Nested Navigation")
        print("=" * 50)
        
        if not self.client:
            self.log_test("Nested Navigation", False, "No qBittorrent client available")
            return
            
        if not accessible_paths:
            self.log_test("Nested Navigation", False, "No accessible paths to test")
            return
        
        for base_path in accessible_paths[:3]:  # Test first 3 accessible paths
            try:
                contents = self.client.app_get_directory_content(base_path)
                entries = [str(item) for item in contents]
                
                # Find a subdirectory to navigate into
                subdirs = [entry.rstrip('/') for entry in entries if entry.endswith('/')]
                
                if subdirs:
                    subdir = subdirs[0]
                    subdir_path = f"{base_path.rstrip('/')}/{subdir}"
                    
                    try:
                        sub_contents = self.client.app_get_directory_content(subdir_path)
                        sub_entries = [str(item) for item in sub_contents]
                        
                        self.log_test(
                            f"Navigate {base_path} → {subdir}",
                            True,
                            f"Found {len(sub_entries)} entries in subdirectory",
                            {"parent": base_path, "subdir": subdir_path, "entries": len(sub_entries)}
                        )
                        
                    except Exception as e:
                        self.log_test(f"Navigate {base_path} → {subdir}", False, f"Error: {e}")
                else:
                    self.log_test(f"Navigate {base_path}", True, "No subdirectories found (empty or only files)")
                    
            except Exception as e:
                self.log_test(f"Navigate {base_path}", False, f"Error: {e}")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n⚠️  Testing Edge Cases")
        print("=" * 50)
        
        if not self.client:
            self.log_test("Edge Cases", False, "No qBittorrent client available")
            return
        
        # Test 1: Non-existent path
        try:
            self.client.app_get_directory_content("/definitely/does/not/exist/path")
            self.log_test("Non-existent Path", False, "Should have raised NotFound404Error")
        except qba_exc.NotFound404Error:
            self.log_test("Non-existent Path", True, "Correctly returned 404 for non-existent path")
        except Exception as e:
            self.log_test("Non-existent Path", False, f"Unexpected error type: {e}")
        
        # Test 2: Invalid path characters
        try:
            self.client.app_get_directory_content("/path/with\x00null/character")
            self.log_test("Invalid Path Characters", False, "Should have failed with invalid characters")
        except Exception:
            self.log_test("Invalid Path Characters", True, "Correctly handled invalid path characters")
        
        # Test 3: Empty path
        try:
            contents = self.client.app_get_directory_content("")
            # Empty path might be treated as root
            self.log_test("Empty Path", True, "Empty path handled gracefully")
        except Exception as e:
            self.log_test("Empty Path", True, f"Empty path rejected as expected: {e}")
    
    def test_docker_mapping_comparison(self):
        """Compare qBittorrent paths with Docker mappings if available"""
        print("\n🐳 Testing Docker Mapping Comparison")
        print("=" * 50)
        
        if not self.client:
            self.log_test("Docker Mapping Comparison", False, "No qBittorrent client available")
            return
            
        if not self.docker_mapper:
            self.log_test("Docker Mapping Comparison", True, "No Docker mappings configured - skipping comparison")
            return
        
        # Test accessible paths through qBittorrent vs Docker mapping
        mapped_roots = self.docker_mapper.get_mapped_roots()
        
        for host_path in mapped_roots:
            try:
                container_path = self.docker_mapper.host_to_container(str(host_path))
                
                # Test if container path is accessible via qBittorrent
                try:
                    contents = self.client.app_get_directory_content(container_path)
                    entries = [str(item) for item in contents]
                    
                    self.log_test(
                        f"Docker Mapping {host_path} → {container_path}",
                        True,
                        f"Container path accessible with {len(entries)} entries",
                        {"host_path": str(host_path), "container_path": container_path, "accessible": True}
                    )
                    
                except qba_exc.NotFound404Error:
                    self.log_test(
                        f"Docker Mapping {host_path} → {container_path}",
                        False,
                        "Container path not accessible via qBittorrent",
                        {"host_path": str(host_path), "container_path": container_path, "accessible": False}
                    )
                    
            except Exception as e:
                self.log_test(f"Docker Mapping {host_path}", False, f"Error testing mapping: {e}")
    
    def test_default_save_path(self):
        """Test qBittorrent's default save path"""
        print("\n💾 Testing Default Save Path")
        print("=" * 50)
        
        if not self.client:
            self.log_test("Default Save Path", False, "No qBittorrent client available")
            return
        
        try:
            default_path = self.client.app_default_save_path()
            
            # Try to browse the default save path
            try:
                contents = self.client.app_get_directory_content(default_path)
                entries = [str(item) for item in contents]
                
                self.log_test(
                    "Default Save Path",
                    True,
                    f"Default path {default_path} accessible with {len(entries)} entries",
                    {"default_path": default_path, "accessible": True, "entries": len(entries)}
                )
                
            except qba_exc.NotFound404Error:
                self.log_test(
                    "Default Save Path",
                    False,
                    f"Default path {default_path} not accessible",
                    {"default_path": default_path, "accessible": False}
                )
                
        except Exception as e:
            self.log_test("Default Save Path", False, f"Could not get default save path: {e}")
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n📊 Test Report Summary")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"📈 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test']}: {result['details']}")
        
        # Key findings
        print(f"\n🔍 Key Findings:")
        
        # Check if directory browsing is viable
        browsing_tests = [r for r in self.test_results if "Browse" in r["test"] and r["success"]]
        if browsing_tests:
            print("   ✅ qBittorrent directory browsing is functional")
        else:
            print("   ❌ qBittorrent directory browsing may not be viable")
        
        # Check navigation capabilities
        nav_tests = [r for r in self.test_results if "Navigate" in r["test"] and r["success"]]
        if nav_tests:
            print("   ✅ Nested directory navigation works")
        else:
            print("   ⚠️  Nested navigation may have limitations")
        
        # Docker mapping comparison
        docker_tests = [r for r in self.test_results if "Docker Mapping" in r["test"]]
        if docker_tests:
            docker_success = [r for r in docker_tests if r["success"]]
            if docker_success:
                print("   ✅ Docker mapped paths are accessible via qBittorrent")
            else:
                print("   ⚠️  Docker mapped paths may not be accessible via qBittorrent")
        
        # Save detailed report
        report_file = "qbit_navigation_test_report.json"
        with open(report_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "results": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Recommendation
        print(f"\n🎯 Recommendation:")
        if passed_tests >= total_tests * 0.8:  # 80% success rate
            print("   ✅ qBittorrent API navigation appears viable for migration!")
            print("   💚 Proceed with Phase 2 of the migration plan.")
        else:
            print("   ⚠️  qBittorrent API navigation may have issues.")
            print("   🔄 Consider addressing failed tests before proceeding.")
        
        return passed_tests >= total_tests * 0.8
    
    def run_all_tests(self):
        """Run all navigation tests"""
        print("🧪 qBittorrent Directory Navigation API Test")
        print("=" * 60)
        print("Testing qBittorrent's app_get_directory_content() API")
        print("to validate directory browsing capabilities before migration.")
        print()
        
        # Test 1: Connection
        if not self.connect_to_qbittorrent():
            print("❌ Cannot continue without qBittorrent connection")
            return False
        
        # Test 2: Directory browsing
        accessible_paths = self.test_directory_browsing()
        
        # Test 3: Nested navigation
        if accessible_paths:
            self.test_nested_navigation(accessible_paths)
        
        # Test 4: Edge cases
        self.test_edge_cases()
        
        # Test 5: Docker mapping comparison
        self.test_docker_mapping_comparison()
        
        # Test 6: Default save path
        self.test_default_save_path()
        
        # Generate report
        return self.generate_report()


def main():
    """Main test runner"""
    tester = QBitNavigationTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
    finally:
        # Clean up
        if tester.client:
            try:
                tester.client.auth_log_out()
                print("🧹 Logged out from qBittorrent")
            except:
                pass


if __name__ == "__main__":
    main()
