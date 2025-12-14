# ============================================================================
# Gamification Tests
# ============================================================================
import pytest
from app.services.gamification.xp_system import XPSystem

class TestXPSystem:
    """Tests for XP and leveling system"""
    
    def test_level_calculation(self):
        """Test level calculation from XP"""
        system = XPSystem(None)
        
        # Level 1: 0 XP
        assert system._calculate_level(0) == 1
        
        # Level 2: 100 XP
        assert system._calculate_level(100) == 2
        
        # Level 5: 1000 XP
        assert system._calculate_level(1000) == 5
        
        # Level 10: 5500 XP
        assert system._calculate_level(5500) == 10
    
    def test_level_info(self):
        """Test level info retrieval"""
        system = XPSystem(None)
        
        info = system.get_level_info(1500)
        
        assert info["level"] == 6
        assert info["title"] == "Subject Explorer"
        assert "progress_percent" in info
    
    def test_xp_values(self):
        """Test XP value constants"""
        assert XPSystem.XP_VALUES["correct_easy"] == 5
        assert XPSystem.XP_VALUES["correct_hard"] == 20
        assert XPSystem.XP_VALUES["streak_7_days"] == 100


# Run tests with: pytest tests/ -v --asyncio-mode=auto