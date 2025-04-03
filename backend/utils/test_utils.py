"""
test_utils.py - Simple test script for the utils module.

This script tests basic functionality of the utils module components.
"""

import os
import logging
from typing import Dict, Any

# Import from the utils module
from . import (
    setup_logger,
    get_logger,
    LoggerMixin,
    ensure_dir,
    safe_filename,
    get_file_extension,
    is_valid_url,
    is_valid_nfc_uid,
    sanitize_input,
    event_bus,
    EventNames,
    get_system_info,
    AppError,
    ValidationError
)


def run_tests() -> Dict[str, Any]:
    """Run basic tests for the utils module and return results."""
    results = {
        'tests_run': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'failures': []
    }
    
    def run_test(name, test_fn):
        """Run a single test and update results."""
        results['tests_run'] += 1
        try:
            test_fn()
            print(f"✅ {name}: Passed")
            results['tests_passed'] += 1
        except Exception as e:
            print(f"❌ {name}: Failed - {str(e)}")
            results['tests_failed'] += 1
            results['failures'].append({
                'name': name,
                'error': str(e)
            })
    
    # Test logger.py
    def test_logger():
        logger = setup_logger("test_logger", level=logging.DEBUG)
        assert logger.name == "test_logger"
        
        # Test LoggerMixin
        class TestClass(LoggerMixin):
            def __init__(self):
                self.setup_logger()
                
        test_obj = TestClass()
        assert test_obj.logger is not None
        assert test_obj.logger.name == "TestClass"
        
    run_test("Logger Module", test_logger)
    
    # Test file_utils.py
    def test_file_utils():
        test_dir = "test_dir"
        ensure_dir(test_dir)
        assert os.path.exists(test_dir)
        
        # Test safe_filename
        safe_name = safe_filename("test:file?.txt")
        assert safe_name == "test_file_.txt"
        
        # Test get_file_extension
        ext = get_file_extension("example.mp3")
        assert ext == "mp3"
        
        # Clean up
        if os.path.exists(test_dir):
            os.rmdir(test_dir)
            
    run_test("File Utils Module", test_file_utils)
    
    # Test validators.py
    def test_validators():
        try:
            # Test URL validation
            result1 = is_valid_url("https://example.com")
            print(f"  URL validation test 1: {result1}")
            assert result1 == True
            
            result2 = is_valid_url("not-a-url")
            print(f"  URL validation test 2: {result2}")
            assert result2 == False
            
            # Test NFC UID validation - valid 8 character hex string
            result3 = is_valid_nfc_uid("1A2B3C4D")
            print(f"  NFC UID validation test 1: {result3}")
            assert result3 == True
            
            result4 = is_valid_nfc_uid("XYZ")
            print(f"  NFC UID validation test 2: {result4}")
            assert result4 == False
            
            # Test sanitization
            sanitized = sanitize_input("<script>alert('xss')</script>")
            print(f"  Sanitization result: {sanitized}")
            assert "<" not in sanitized
        except Exception as e:
            print(f"  DEBUG - validators test failed: {str(e)}")
            raise
        
    run_test("Validators Module", test_validators)
    
    # Test event_bus.py
    def test_event_bus():
        test_data = {'called': False}
        
        def test_handler(tag_uid):
            test_data['called'] = True
            test_data['tag_uid'] = tag_uid
            
        event_bus.on(EventNames.TAG_DETECTED, test_handler)
        event_bus.emit(EventNames.TAG_DETECTED, tag_uid="1A2B3C4D")
        
        assert test_data['called'] is True
        assert test_data['tag_uid'] == "1A2B3C4D"
        
        # Clean up
        event_bus.off(EventNames.TAG_DETECTED, test_handler)
        
    run_test("Event Bus Module", test_event_bus)
    
    # Test system_utils.py
    def test_system_utils():
        info = get_system_info()
        assert 'os_name' in info
        assert 'hostname' in info
        
    run_test("System Utils Module", test_system_utils)
    
    # Test exceptions.py
    def test_exceptions():
        # Test basic exceptions
        try:
            raise AppError("Test error", {"detail": "test"})
            assert False  # Should not reach here
        except AppError as e:
            assert e.message == "Test error"
            assert e.details.get("detail") == "test"
            
        # Test validation error
        try:
            raise ValidationError("Invalid input")
            assert False  # Should not reach here
        except AppError as e:
            # ValidationError should be catchable as AppError (inheritance)
            assert e.message == "Invalid input"
            
    run_test("Exceptions Module", test_exceptions)
    
    # Print summary
    print("\n----- Test Summary -----")
    print(f"Tests Run: {results['tests_run']}")
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Tests Failed: {results['tests_failed']}")
    
    if results['failures']:
        print("\nFailures:")
        for failure in results['failures']:
            print(f"  - {failure['name']}: {failure['error']}")
    
    return results


if __name__ == "__main__":
    print("Running utils module tests...")
    run_tests()
