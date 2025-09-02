"""
Minimal pooling support for RAG-Anything and LightRAG
This module provides pooling capabilities without modifying core RAG-Anything/LightRAG code
"""

import asyncio
import hashlib
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pickle
import os
from pathlib import Path

@dataclass
class InstanceState:
    """State information for a poolable instance"""
    instance_id: str
    workspace: str
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    is_healthy: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_usage(self):
        """Update usage statistics"""
        self.last_used_at = datetime.now()
        self.use_count += 1


class PoolableRAGAnything:
    """
    Wrapper for RAGAnything instance with pooling support
    """
    
    def __init__(self, instance, state: InstanceState):
        """
        Initialize poolable wrapper
        
        Args:
            instance: RAGAnything instance
            state: Instance state information
        """
        self.instance = instance
        self.state = state
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire lock for exclusive access"""
        await self._lock.acquire()
        self.state.update_usage()
        
    def release(self):
        """Release lock after usage"""
        if self._lock.locked():
            self._lock.release()
            
    async def health_check(self) -> bool:
        """
        Check if instance is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Simple health check - verify LightRAG is initialized
            if hasattr(self.instance, 'lightrag'):
                await self.instance._ensure_lightrag_initialized()
                self.state.is_healthy = True
                return True
            self.state.is_healthy = False
            return False
        except Exception:
            self.state.is_healthy = False
            return False
            
    def get_state_key(self) -> str:
        """
        Generate unique key for instance state
        
        Returns:
            str: State key based on workspace
        """
        return hashlib.md5(self.state.workspace.encode()).hexdigest()
        
    async def save_state(self, path: str):
        """
        Save instance state to disk
        
        Args:
            path: Directory to save state
        """
        state_file = f"{path}/{self.get_state_key()}.pkl"
        async with asyncio.Lock():
            with open(state_file, 'wb') as f:
                pickle.dump({
                    'state': self.state,
                    'metadata': self.get_metadata()
                }, f)
                
    async def load_state(self, path: str) -> bool:
        """
        Load instance state from disk
        
        Args:
            path: Directory to load state from
            
        Returns:
            bool: True if loaded successfully
        """
        state_file = f"{path}/{self.get_state_key()}.pkl"
        try:
            async with asyncio.Lock():
                with open(state_file, 'rb') as f:
                    data = pickle.load(f)
                    self.state = data['state']
                    return True
        except FileNotFoundError:
            return False
            
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get instance metadata
        
        Returns:
            dict: Instance metadata
        """
        return {
            'instance_id': self.state.instance_id,
            'workspace': self.state.workspace,
            'created_at': self.state.created_at.isoformat(),
            'last_used_at': self.state.last_used_at.isoformat(),
            'use_count': self.state.use_count,
            'is_healthy': self.state.is_healthy,
            'custom_metadata': self.state.metadata
        }
        
    def should_evict(self, max_idle_seconds: int = 3600) -> bool:
        """
        Check if instance should be evicted based on idle time
        
        Args:
            max_idle_seconds: Maximum idle time in seconds
            
        Returns:
            bool: True if should be evicted
        """
        idle_time = (datetime.now() - self.state.last_used_at).total_seconds()
        return idle_time > max_idle_seconds or not self.state.is_healthy


class PoolingMixin:
    """
    Mixin to add pooling capabilities to RAGAnything
    """
    
    def make_poolable(self) -> PoolableRAGAnything:
        """
        Convert RAGAnything instance to poolable wrapper
        
        Returns:
            PoolableRAGAnything: Wrapped instance
        """
        import uuid
        
        state = InstanceState(
            instance_id=str(uuid.uuid4()),
            workspace=getattr(self, 'working_dir', 'default')
        )
        
        return PoolableRAGAnything(self, state)
        
    @classmethod
    def create_poolable_instance(cls, workspace: str, config: Dict[str, Any]) -> PoolableRAGAnything:
        """
        Factory method to create poolable instance
        
        Args:
            workspace: Workspace directory
            config: Configuration dictionary
            
        Returns:
            PoolableRAGAnything: New poolable instance
        """
        import uuid
        
        # Create RAGAnything instance with workspace
        config['working_dir'] = workspace
        instance = cls(**config)
        
        # Create state
        state = InstanceState(
            instance_id=str(uuid.uuid4()),
            workspace=workspace
        )
        
        return PoolableRAGAnything(instance, state)


# Utility functions for pool management

def create_instance_key(workspace: str, tenant_id: Optional[str] = None) -> str:
    """
    Create unique key for instance lookup
    
    Args:
        workspace: Workspace directory
        tenant_id: Optional tenant identifier
        
    Returns:
        str: Unique instance key
    """
    key_parts = [workspace]
    if tenant_id:
        key_parts.append(tenant_id)
    
    key_string = "|".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()


def parse_instance_key(key: str) -> Tuple[str, Optional[str]]:
    """
    Parse instance key to extract components
    
    Args:
        key: Instance key
        
    Returns:
        tuple: (workspace, tenant_id)
    """
    # This is a simplified version - in production would need reverse mapping
    # For now, return placeholder values
    return ("workspace", None)


async def warm_up_instance(poolable: PoolableRAGAnything) -> bool:
    """
    Warm up instance by initializing components
    
    Args:
        poolable: Poolable instance
        
    Returns:
        bool: True if warmed up successfully
    """
    try:
        # Initialize LightRAG
        await poolable.instance._ensure_lightrag_initialized()
        
        # Perform health check
        is_healthy = await poolable.health_check()
        
        return is_healthy
    except Exception:
        return False


class PoolableLightRAG:
    """
    Wrapper for LightRAG instance with pooling support
    """
    
    def __init__(self, instance, state: InstanceState):
        """
        Initialize poolable LightRAG wrapper
        
        Args:
            instance: LightRAG instance
            state: Instance state information
        """
        self.instance = instance
        self.state = state
        self._lock = asyncio.Lock()
        self._reference_count = 0
        
    async def acquire(self):
        """Acquire lock for exclusive access"""
        await self._lock.acquire()
        self.state.update_usage()
        # Atomic increment
        self._reference_count += 1
        
    def release(self):
        """Release lock after usage"""
        if self._lock.locked():
            # Atomic decrement with minimum bound
            self._reference_count = max(0, self._reference_count - 1)
            self._lock.release()
            
    async def health_check(self) -> bool:
        """
        Check if LightRAG instance is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # Check working directory exists
            if hasattr(self.instance, 'working_dir'):
                if not os.path.exists(self.instance.working_dir):
                    Path(self.instance.working_dir).mkdir(parents=True, exist_ok=True)
                self.state.is_healthy = True
                return True
            self.state.is_healthy = False
            return False
        except Exception:
            self.state.is_healthy = False
            return False
            
    def get_state_key(self) -> str:
        """
        Generate unique key for instance state
        
        Returns:
            str: State key based on workspace
        """
        return hashlib.md5(self.state.workspace.encode()).hexdigest()


class LightRAGPoolingMixin:
    """
    Mixin to add pooling capabilities to LightRAG
    """
    
    def make_poolable(self) -> PoolableLightRAG:
        """
        Convert LightRAG instance to poolable wrapper
        
        Returns:
            PoolableLightRAG: Wrapped instance
        """
        import uuid
        
        state = InstanceState(
            instance_id=str(uuid.uuid4()),
            workspace=getattr(self, 'working_dir', 'default')
        )
        
        return PoolableLightRAG(self, state)
        
    @classmethod
    def create_poolable_instance(cls, workspace: str, config: Dict[str, Any]) -> PoolableLightRAG:
        """
        Factory method to create poolable LightRAG instance
        
        Args:
            workspace: Workspace directory
            config: Configuration dictionary
            
        Returns:
            PoolableLightRAG: New poolable instance
        """
        import uuid
        
        # Ensure workspace exists
        Path(workspace).mkdir(parents=True, exist_ok=True)
        
        # Create LightRAG instance with workspace
        config['working_dir'] = workspace
        instance = cls(**config)
        
        # Create state
        state = InstanceState(
            instance_id=str(uuid.uuid4()),
            workspace=workspace
        )
        
        return PoolableLightRAG(instance, state)


class InstanceMetrics:
    """Metrics collection for instance pool"""
    
    def __init__(self):
        self.total_created = 0
        self.total_evicted = 0
        self.total_acquisitions = 0
        self.total_releases = 0
        self.health_check_failures = 0
        self.creation_errors = 0
        
    def record_creation(self):
        self.total_created += 1
        
    def record_eviction(self):
        self.total_evicted += 1
        
    def record_acquisition(self):
        self.total_acquisitions += 1
        
    def record_release(self):
        self.total_releases += 1
        
    def record_health_failure(self):
        self.health_check_failures += 1
        
    def record_creation_error(self):
        self.creation_errors += 1
        
    def get_stats(self) -> Dict[str, int]:
        """Get current statistics"""
        return {
            'total_created': self.total_created,
            'total_evicted': self.total_evicted,
            'total_acquisitions': self.total_acquisitions,
            'total_releases': self.total_releases,
            'health_check_failures': self.health_check_failures,
            'creation_errors': self.creation_errors,
            'active_instances': self.total_created - self.total_evicted
        }
