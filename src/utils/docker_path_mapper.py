"""
Docker Path Mapping Utilities
Handles translation between host and container paths for Docker deployments
"""
from pathlib import Path
from typing import Dict, Optional, Tuple


class DockerPathMapper:
    """Handles path translation between host and container paths"""
    
    def __init__(self, path_mapping: Dict[str, str] = None):
        """
        Initialize with docker path mapping configuration
        
        Args:
            path_mapping: Dict mapping host paths to container paths
                         e.g. {"/mnt/user/data": "/data"}
        """
        self.path_mapping = path_mapping or {}
        
        # Sort mappings by host path length (longest first) for proper matching
        self.sorted_mappings = sorted(
            self.path_mapping.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
    
    def host_to_container(self, host_path: str) -> str:
        """
        Convert host path to container path
        
        Args:
            host_path: Path as seen on the host system
            
        Returns:
            Container path that qBittorrent will understand
        """
        if not self.path_mapping:
            return host_path
        
        host_path = str(Path(host_path).resolve())
        
        # Find the best matching mapping (longest path match)
        for host_prefix, container_prefix in self.sorted_mappings:
            host_prefix = str(Path(host_prefix).resolve())
            if host_path.startswith(host_prefix):
                # Replace the host prefix with container prefix
                relative_path = host_path[len(host_prefix):].lstrip('/')
                if relative_path:
                    return f"{container_prefix.rstrip('/')}/{relative_path}"
                else:
                    return container_prefix.rstrip('/')
        
        # No mapping found, return original path
        return host_path
    
    def container_to_host(self, container_path: str) -> str:
        """
        Convert container path to host path
        
        Args:
            container_path: Path as seen inside the container
            
        Returns:
            Host path that users can navigate to
        """
        if not self.path_mapping:
            return container_path
        
        container_path = str(Path(container_path))
        
        # Find the best matching mapping (longest path match)
        for host_prefix, container_prefix in self.sorted_mappings:
            if container_path.startswith(container_prefix):
                # Replace the container prefix with host prefix
                relative_path = container_path[len(container_prefix):].lstrip('/')
                if relative_path:
                    return f"{host_prefix.rstrip('/')}/{relative_path}"
                else:
                    return host_prefix.rstrip('/')
        
        # No mapping found, return original path
        return container_path
    
    def is_path_mapped(self, host_path: str) -> bool:
        """
        Check if a host path has a container mapping
        
        Args:
            host_path: Path to check
            
        Returns:
            True if path is within a mapped directory
        """
        if not self.path_mapping:
            return False
        
        host_path = str(Path(host_path).resolve())
        
        for host_prefix, _ in self.sorted_mappings:
            host_prefix = str(Path(host_prefix).resolve())
            if host_path.startswith(host_prefix):
                return True
        
        return False
    
    def get_mapped_roots(self) -> list:
        """
        Get list of host root paths that are mapped to containers
        
        Returns:
            List of host paths that have container mappings
        """
        return [Path(host_path).resolve() for host_path, _ in self.path_mapping.items()]
    
    def get_path_info(self, host_path: str) -> dict:
        """
        Get comprehensive path mapping information
        
        Args:
            host_path: Host path to analyze
            
        Returns:
            Dict with path mapping details
        """
        host_path_resolved = str(Path(host_path).resolve())
        container_path = self.host_to_container(host_path)
        is_mapped = self.is_path_mapped(host_path)
        
        # Find which mapping rule was used
        mapping_rule = None
        if is_mapped:
            for host_prefix, container_prefix in self.sorted_mappings:
                host_prefix_resolved = str(Path(host_prefix).resolve())
                if host_path_resolved.startswith(host_prefix_resolved):
                    mapping_rule = {
                        "host_prefix": host_prefix,
                        "container_prefix": container_prefix,
                        "host_prefix_resolved": host_prefix_resolved
                    }
                    break
        
        return {
            "host_path": host_path,
            "host_path_resolved": host_path_resolved,
            "container_path": container_path,
            "is_mapped": is_mapped,
            "mapping_rule": mapping_rule,
            "all_mappings": self.path_mapping
        }
    
    def validate_mapping(self) -> Dict[str, list]:
        """
        Validate docker path mappings
        
        Returns:
            Dict with validation results and any issues found
        """
        issues = []
        warnings = []
        
        for host_path, container_path in self.path_mapping.items():
            # Check if host path exists
            if not Path(host_path).exists():
                warnings.append(f"Host path does not exist: {host_path}")
            
            # Check for overlapping mappings
            for other_host, other_container in self.path_mapping.items():
                if host_path != other_host:
                    if (Path(host_path).resolve().is_relative_to(Path(other_host).resolve()) or
                        Path(other_host).resolve().is_relative_to(Path(host_path).resolve())):
                        issues.append(f"Overlapping mappings: {host_path} and {other_host}")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "is_valid": len(issues) == 0
        }
