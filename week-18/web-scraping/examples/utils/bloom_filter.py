"""Bloom filter for efficient URL deduplication.

This module implements a space-efficient probabilistic data structure
for testing set membership.
"""

import hashlib
import math
from typing import Optional


class BloomFilter:
    """Space-efficient probabilistic data structure for set membership testing.
    
    A Bloom filter is a bit array with multiple hash functions. It can tell
    if an element is definitely not in the set, or possibly in the set.
    False positives are possible, but false negatives are not.
    """
    
    def __init__(self, 
                 expected_elements: int = 100000,
                 false_positive_rate: float = 0.01):
        """Initialize Bloom filter.
        
        Args:
            expected_elements: Expected number of elements to store
            false_positive_rate: Desired false positive probability (0-1)
        """
        self.expected_elements = expected_elements
        self.false_positive_rate = false_positive_rate
        
        # Calculate optimal bit array size
        self.size = self._optimal_size(expected_elements, false_positive_rate)
        
        # Calculate optimal number of hash functions
        self.num_hashes = self._optimal_hash_count(self.size, expected_elements)
        
        # Initialize bit array
        self.bit_array = [False] * self.size
        
        # Track actual elements added
        self.count = 0
    
    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        """Calculate optimal bit array size.
        
        Args:
            n: Expected number of elements
            p: False positive probability
            
        Returns:
            Optimal size in bits
        """
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(math.ceil(m))
    
    @staticmethod
    def _optimal_hash_count(m: int, n: int) -> int:
        """Calculate optimal number of hash functions.
        
        Args:
            m: Bit array size
            n: Expected number of elements
            
        Returns:
            Optimal number of hash functions
        """
        k = (m / n) * math.log(2)
        return max(1, int(math.ceil(k)))
    
    def _hashes(self, item: str) -> list[int]:
        """Generate hash values for an item.
        
        Uses double hashing technique with MD5 and SHA256.
        
        Args:
            item: Item to hash
            
        Returns:
            List of hash positions
        """
        # Use two different hash functions
        h1 = int(hashlib.md5(item.encode()).hexdigest(), 16)
        h2 = int(hashlib.sha256(item.encode()).hexdigest(), 16)
        
        # Generate k hash values using double hashing
        positions = []
        for i in range(self.num_hashes):
            # Combine hashes: h(i) = h1 + i*h2
            hash_val = (h1 + i * h2) % self.size
            positions.append(hash_val)
        
        return positions
    
    def add(self, item: str) -> None:
        """Add an item to the filter.
        
        Args:
            item: Item to add
        """
        for pos in self._hashes(item):
            self.bit_array[pos] = True
        self.count += 1
    
    def contains(self, item: str) -> bool:
        """Check if an item might be in the set.
        
        Args:
            item: Item to check
            
        Returns:
            True if possibly in set, False if definitely not in set
        """
        return all(self.bit_array[pos] for pos in self._hashes(item))
    
    def __contains__(self, item: str) -> bool:
        """Support 'in' operator."""
        return self.contains(item)
    
    @property
    def current_false_positive_rate(self) -> float:
        """Calculate current false positive rate based on elements added.
        
        Returns:
            Estimated current false positive probability
        """
        if self.count == 0:
            return 0.0
        
        # Formula: (1 - e^(-k*n/m))^k
        exponent = -self.num_hashes * self.count / self.size
        return (1 - math.exp(exponent)) ** self.num_hashes
    
    def __len__(self) -> int:
        """Return number of elements added."""
        return self.count
    
    def stats(self) -> dict:
        """Get statistics about the Bloom filter.
        
        Returns:
            Dictionary with filter statistics
        """
        return {
            'size': self.size,
            'num_hashes': self.num_hashes,
            'elements_added': self.count,
            'expected_elements': self.expected_elements,
            'target_fp_rate': self.false_positive_rate,
            'current_fp_rate': self.current_false_positive_rate,
            'capacity_used': self.count / self.expected_elements if self.expected_elements > 0 else 0,
        }
