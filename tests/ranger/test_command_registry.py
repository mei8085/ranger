# -*- coding: utf-8 -*-
"""
Test cases for verifying the CommandRegistry implementation
ensures backward compatibility with the original CommandContainer.

These tests verify:
1. Command registration and lookup
2. Alias creation and resolution
3. Error messages and behavior
4. Abbreviation support
5. Command generation for tab completion
"""

from __future__ import (absolute_import, division, print_function)

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ranger.api.commands import Command, CommandContainer, command_alias_factory, command_function_factory
from ranger.api.command_registry import CommandRegistry


class _MockFileManager:
    """Mock file manager for testing."""
    def __init__(self):
        self.notifications = []
    
    def notify(self, message, bad=False):
        self.notifications.append((message, bad))
    
    def clear_notifications(self):
        """Clear all collected notifications."""
        self.notifications = []


class _SampleCommand(Command):
    """Sample command class for testing."""
    def execute(self):
        pass


class _SampleCommandNoAbbrev(Command):
    """Sample command that doesn't allow abbreviation."""
    allow_abbrev = False
    name = 'test_no_abbrev'


class _AnotherSampleCommand(Command):
    """Another sample command for testing."""
    name = 'another_test'


class TestCommandRegistryBasics(unittest.TestCase):
    """Test basic functionality of CommandRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        
        # Set up mock file manager
        self.fm = _MockFileManager()
        self.registry.fm = self.fm
        self.container.fm = self.fm
    
    def test_inheritance(self):
        """Test that CommandContainer inherits from CommandRegistry."""
        self.assertTrue(issubclass(CommandContainer, CommandRegistry))
    
    def test_initial_state(self):
        """Test initial state of the registry."""
        self.assertEqual(self.registry.commands, {})
        self.assertEqual(self.container.commands, {})
    
    def test_commands_property(self):
        """Test that commands property returns the internal dict."""
        self.assertIs(self.registry.commands, self.registry._commands)
        self.assertIs(self.container.commands, self.container._commands)
    
    def test_getitem(self):
        """Test __getitem__ method."""
        # Register a command first
        self.registry._commands['test'] = _SampleCommand
        
        # Test that we can access it via []
        self.assertIs(self.registry['test'], _SampleCommand)
        
        # Test that it raises KeyError for non-existent commands
        with self.assertRaises(KeyError):
            _ = self.registry['nonexistent']


class TestCommandRegistration(unittest.TestCase):
    """Test command registration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        self.fm = _MockFileManager()
        self.registry.fm = self.fm
        self.container.fm = self.fm
    
    def test_register_method(self):
        """Test the register method."""
        self.registry.register('test_cmd', _SampleCommand)
        
        self.assertIn('test_cmd', self.registry.commands)
        self.assertIsNotNone(self.registry.get_command('test_cmd'))
    
    def test_load_commands_from_module(self):
        """Test loading commands from a module."""
        # Create a mock module
        mock_module = Mock()
        mock_module._SampleCommand = _SampleCommand
        mock_module._AnotherSampleCommand = _AnotherSampleCommand
        mock_module.NotACommand = "not a command"
        mock_module.__dict__ = {
            '_SampleCommand': _SampleCommand,
            '_AnotherSampleCommand': _AnotherSampleCommand,
            'NotACommand': "not a command",
            'Command': Command  # Should be excluded
        }
        
        self.registry.load_commands_from_module(mock_module)
        
        # Check that commands are loaded
        self.assertIn('_SampleCommand', self.registry.commands)
        self.assertIn('another_test', self.registry.commands)
        
        # Check that non-commands are not loaded
        self.assertNotIn('NotACommand', self.registry.commands)
        
        # Check that base Command class is not loaded
        self.assertNotIn('Command', self.registry.commands)
    
    def test_load_commands_from_object(self):
        """Test loading commands from an object."""
        class _TestObject:
            def method1(self):
                pass
            def method2(self):
                pass
            def _private_method(self):
                pass
        
        obj = _TestObject()
        filtr = {'method1', 'method2', 'excluded'}
        
        self.registry.load_commands_from_object(obj, filtr)
        
        # Check that public methods in filtr are loaded
        self.assertIn('method1', self.registry.commands)
        self.assertIn('method2', self.registry.commands)
        
        # Check that private methods are not loaded
        self.assertNotIn('_private_method', self.registry.commands)
        
        # Check that methods not in filtr are not loaded
        self.assertNotIn('excluded', self.registry.commands)


class TestCommandLookup(unittest.TestCase):
    """Test command lookup functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        self.fm = _MockFileManager()
        self.registry.fm = self.fm
        self.container.fm = self.fm
        
        # Register some test commands
        self.registry._commands['test_command'] = _SampleCommand
        self.registry._commands['test_no_abbrev'] = _SampleCommandNoAbbrev
        self.registry._commands['another_test'] = _AnotherSampleCommand
        
        self.container._commands['test_command'] = _SampleCommand
        self.container._commands['test_no_abbrev'] = _SampleCommandNoAbbrev
        self.container._commands['another_test'] = _AnotherSampleCommand
    
    def test_get_command_exact_match(self):
        """Test exact command lookup."""
        # Test with exact match
        cmd = self.registry.get_command('test_command')
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd, _SampleCommand)
        
        # Test with non-existent command
        cmd = self.registry.get_command('nonexistent')
        self.assertIsNone(cmd)
    
    def test_get_command_abbrev(self):
        """Test command lookup with abbreviation."""
        # Test with abbreviation that matches one command
        cmd = self.registry.get_command('test_com', abbrev=True)
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd, _SampleCommand)
        
        # Test with abbreviation that matches exact name
        cmd = self.registry.get_command('test_command', abbrev=True)
        self.assertEqual(cmd, _SampleCommand)
        
        # Test with non-existent command (should raise KeyError)
        with self.assertRaises(KeyError):
            self.registry.get_command('nonexistent', abbrev=True)
    
    def test_get_command_abbrev_ambiguous(self):
        """Test ambiguous abbreviation raises ValueError."""
        # Both 'test_command' and 'test_no_abbrev' start with 'test'
        # But 'test_no_abbrev' has allow_abbrev=False, so it shouldn't match
        cmd = self.registry.get_command('test', abbrev=True)
        # Should return test_command since test_no_abbrev doesn't allow abbrev
        self.assertEqual(cmd, _SampleCommand)
    
    def test_get_command_no_abbrev(self):
        """Test that commands with allow_abbrev=False don't match abbreviations."""
        # test_no_abbrev has allow_abbrev=False
        # So 'test_no' should NOT match it
        with self.assertRaises(KeyError):
            self.registry.get_command('test_no', abbrev=True)
        
        # But exact match should work
        cmd = self.registry.get_command('test_no_abbrev', abbrev=True)
        self.assertEqual(cmd, _SampleCommandNoAbbrev)


class TestCommandAlias(unittest.TestCase):
    """Test command alias functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        self.fm = _MockFileManager()
        self.registry.fm = self.fm
        self.container.fm = self.fm
        
        # Register a test command
        self.registry._commands['test_command'] = _SampleCommand
        self.container._commands['test_command'] = _SampleCommand
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear notifications to avoid affecting other tests
        self.fm.clear_notifications()
    
    def test_alias_creation(self):
        """Test creating an alias."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm.notifications), 0)
        
        self.registry.alias('tc', 'test_command arg1 arg2')
        
        # Check that alias is created
        self.assertIn('tc', self.registry.commands)
        
        # Check that we can look it up
        alias_class = self.registry.get_command('tc')
        self.assertIsNotNone(alias_class)
        
        # Verify it's an alias of _SampleCommand
        self.assertTrue(issubclass(alias_class, _SampleCommand))
        
        # Verify no error notifications were generated
        self.assertEqual(len(self.fm.notifications), 0)
    
    def test_alias_nonexistent_command(self):
        """Test alias creation for non-existent command."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm.notifications), 0)
        
        self.registry.alias('invalid', 'nonexistent_command')
        
        # Check that error was notified
        self.assertEqual(len(self.fm.notifications), 1)
        message, bad = self.fm.notifications[0]
        self.assertTrue(bad)
        self.assertIn('alias failed', message)
        self.assertIn('nonexistent_command', message)
        
        # Check that alias was NOT created
        self.assertNotIn('invalid', self.registry.commands)
    
    def test_alias_error_message_format(self):
        """Test that error message format matches original."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm.notifications), 0)
        
        self.registry.alias('invalid', 'bad_command')
        
        # Verify exactly one notification
        self.assertEqual(len(self.fm.notifications), 1)
        
        message, _ = self.fm.notifications[0]
        # Original format: 'alias failed: No such command: {0}'
        self.assertEqual(message, 'alias failed: No such command: bad_command')


class TestCommandGenerator(unittest.TestCase):
    """Test command generator for tab completion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        self.fm = _MockFileManager()
        self.registry.fm = self.fm
        self.container.fm = self.fm
        
        # Register some test commands
        self.registry._commands['alpha'] = _SampleCommand
        self.registry._commands['beta'] = _SampleCommand
        self.registry._commands['aleph'] = _SampleCommand
    
    def test_command_generator(self):
        """Test command generator."""
        # Test with empty prefix
        result = list(self.registry.command_generator(''))
        self.assertEqual(len(result), 3)
        self.assertTrue(all(cmd.endswith(' ') for cmd in result))
        
        # Test with prefix 'al'
        result = list(self.registry.command_generator('al'))
        self.assertEqual(len(result), 2)
        self.assertIn('alpha ', result)
        self.assertIn('aleph ', result)
        
        # Test with prefix 'be'
        result = list(self.registry.command_generator('be'))
        self.assertEqual(len(result), 1)
        self.assertIn('beta ', result)
        
        # Test with non-matching prefix
        result = list(self.registry.command_generator('xyz'))
        self.assertEqual(len(result), 0)
    
    def test_command_generator_sorted(self):
        """Test that command generator returns sorted results."""
        result = list(self.registry.command_generator(''))
        # Should be sorted alphabetically
        self.assertEqual(result, ['aleph ', 'alpha ', 'beta '])


class TestBehavioralConsistency(unittest.TestCase):
    """Test that CommandRegistry and CommandContainer behave identically."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = CommandRegistry()
        self.container = CommandContainer()
        self.fm_registry = _MockFileManager()
        self.fm_container = _MockFileManager()
        self.registry.fm = self.fm_registry
        self.container.fm = self.fm_container
    
    def tearDown(self):
        """Clean up after each test."""
        # Clear notifications to avoid affecting other tests
        self.fm_registry.clear_notifications()
        self.fm_container.clear_notifications()
    
    def test_commands_dict_access(self):
        """Test that commands dict is accessible."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        # Both should have commands attribute
        self.assertTrue(hasattr(self.registry, 'commands'))
        self.assertTrue(hasattr(self.container, 'commands'))
        
        # Both should be dicts
        self.assertIsInstance(self.registry.commands, dict)
        self.assertIsInstance(self.container.commands, dict)
        
        # Verify no notifications were generated
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
    
    def test_getitem_behavior(self):
        """Test __getitem__ behavior."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        self.registry._commands['test'] = _SampleCommand
        self.container._commands['test'] = _SampleCommand
        
        # Both should return the same value
        self.assertIs(self.registry['test'], self.container['test'])
        
        # Both should raise KeyError for non-existent
        with self.assertRaises(KeyError):
            _ = self.registry['nonexistent']
        with self.assertRaises(KeyError):
            _ = self.container['nonexistent']
        
        # Verify no notifications were generated
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
    
    def test_get_command_behavior(self):
        """Test get_command behavior consistency."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        self.registry._commands['test_cmd'] = _SampleCommand
        self.container._commands['test_cmd'] = _SampleCommand
        
        # Test exact match
        self.assertIs(
            self.registry.get_command('test_cmd'),
            self.container.get_command('test_cmd')
        )
        
        # Test non-existent
        self.assertIs(
            self.registry.get_command('nonexistent'),
            self.container.get_command('nonexistent')
        )
        
        # Verify no notifications were generated
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
    
    def test_get_command_abbrev_behavior(self):
        """Test get_command with abbrev=True behavior consistency."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        self.registry._commands['test_command'] = _SampleCommand
        self.container._commands['test_command'] = _SampleCommand
        
        # Test abbreviation
        self.assertIs(
            self.registry.get_command('test_com', abbrev=True),
            self.container.get_command('test_com', abbrev=True)
        )
        
        # Test KeyError for non-existent
        with self.assertRaises(KeyError):
            self.registry.get_command('nonexistent', abbrev=True)
        with self.assertRaises(KeyError):
            self.container.get_command('nonexistent', abbrev=True)
        
        # Verify no notifications were generated (KeyError is expected, not a notification)
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
    
    def test_alias_error_behavior(self):
        """Test alias error behavior consistency."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        self.registry.alias('invalid', 'bad_cmd')
        self.container.alias('invalid', 'bad_cmd')
        
        # Both should have exactly one notification
        self.assertEqual(len(self.fm_registry.notifications), 1)
        self.assertEqual(len(self.fm_container.notifications), 1)
        
        # Both should have the same error message
        reg_msg, reg_bad = self.fm_registry.notifications[0]
        cont_msg, cont_bad = self.fm_container.notifications[0]
        
        self.assertEqual(reg_msg, cont_msg)
        self.assertEqual(reg_bad, cont_bad)
    
    def test_command_generator_behavior(self):
        """Test command_generator behavior consistency."""
        # Ensure no notifications at start
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)
        
        self.registry._commands['alpha'] = _SampleCommand
        self.registry._commands['beta'] = _SampleCommand
        self.container._commands['alpha'] = _SampleCommand
        self.container._commands['beta'] = _SampleCommand
        
        # Both should return the same results
        reg_result = list(self.registry.command_generator(''))
        cont_result = list(self.container.command_generator(''))
        
        self.assertEqual(reg_result, cont_result)
        
        # Verify no notifications were generated
        self.assertEqual(len(self.fm_registry.notifications), 0)
        self.assertEqual(len(self.fm_container.notifications), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
