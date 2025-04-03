"""
event_bus.py - Event bus for cross-module communication.

This module provides a simple event bus that allows different modules
to communicate with each other without direct dependencies.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from .logger import get_logger

logger = get_logger("event_bus")


class EventBus:
    """
    Simple event bus for cross-module communication.

    Usage:
        # In a module that triggers events:
        from utils.event_bus import event_bus
        event_bus.emit('tag_detected', tag_uid='ABC123')

        # In a module that listens for events:
        from utils.event_bus import event_bus

        def on_tag_detected(tag_uid):
            print(f"Tag detected: {tag_uid}")

        event_bus.on('tag_detected', on_tag_detected)
    """

    def __init__(self):
        """Initialize the event bus."""
        self._events: Dict[str, List[Callable]] = {}
        self._once_events: Dict[str, List[Callable]] = {}
        self._registered_events: Set[str] = set()
        self.logger = logger

    def on(self, event_name: str, callback: Callable) -> None:
        """
        Register an event handler.

        Args:
            event_name (str): Event name
            callback (callable): Function to call when event is emitted
        """
        if event_name not in self._events:
            self._events[event_name] = []
        
        # Add the event to registered events (for documentation purposes)
        self._registered_events.add(event_name)
            
        # Check if callback is already registered
        if callback not in self._events[event_name]:
            self._events[event_name].append(callback)
            self.logger.debug(f"Registered handler for event: {event_name}")
        else:
            self.logger.warning(f"Handler already registered for event: {event_name}")

    def off(self, event_name: str, callback: Optional[Callable] = None) -> None:
        """
        Remove an event handler.

        Args:
            event_name (str): Event name
            callback (callable, optional): Function to remove,
                                           or None to remove all handlers
        """
        # If event doesn't exist, nothing to do
        if event_name not in self._events:
            return
            
        # If callback is None, remove all handlers for this event
        if callback is None:
            self._events[event_name] = []
            self.logger.debug(f"Removed all handlers for event: {event_name}")
            return
            
        # Remove specific callback
        if callback in self._events[event_name]:
            self._events[event_name].remove(callback)
            self.logger.debug(f"Removed handler for event: {event_name}")
            
        # Also check in once_events
        if event_name in self._once_events and callback in self._once_events[event_name]:
            self._once_events[event_name].remove(callback)
            self.logger.debug(f"Removed one-time handler for event: {event_name}")

    def emit(self, event_name: str, **kwargs: Any) -> None:
        """
        Emit an event.

        Args:
            event_name (str): Event name
            **kwargs: Event data
        """
        self.logger.debug(f"Emitting event: {event_name}")
        
        # Process regular event handlers
        if event_name in self._events:
            # Make a copy of the list to avoid issues if handlers modify the list
            handlers = self._events[event_name].copy()
            for callback in handlers:
                try:
                    callback(**kwargs)
                except Exception as e:
                    self.logger.error(f"Error in event handler for {event_name}: {str(e)}")
                    
        # Process one-time event handlers
        if event_name in self._once_events:
            # Make a copy of the list to avoid issues if handlers modify the list
            handlers = self._once_events[event_name].copy()
            # Clear the list first to prevent handlers from being called if they re-emit the same event
            self._once_events[event_name] = []
            for callback in handlers:
                try:
                    callback(**kwargs)
                except Exception as e:
                    self.logger.error(f"Error in one-time event handler for {event_name}: {str(e)}")

    def once(self, event_name: str, callback: Callable) -> None:
        """
        Register an event handler that will be called only once.

        Args:
            event_name (str): Event name
            callback (callable): Function to call when event is emitted
        """
        if event_name not in self._once_events:
            self._once_events[event_name] = []
            
        # Add the event to registered events (for documentation purposes)
        self._registered_events.add(event_name)
            
        # Check if callback is already registered
        if callback not in self._once_events[event_name]:
            self._once_events[event_name].append(callback)
            self.logger.debug(f"Registered one-time handler for event: {event_name}")
        else:
            self.logger.warning(f"One-time handler already registered for event: {event_name}")
            
    def list_events(self) -> Set[str]:
        """
        List all registered event names.
        
        Returns:
            Set[str]: Set of event names
        """
        return self._registered_events
        
    def has_listeners(self, event_name: str) -> bool:
        """
        Check if an event has any listeners.
        
        Args:
            event_name (str): Event name
            
        Returns:
            bool: True if event has listeners
        """
        regular_listeners = event_name in self._events and len(self._events[event_name]) > 0
        once_listeners = event_name in self._once_events and len(self._once_events[event_name]) > 0
        return regular_listeners or once_listeners


# Global event bus instance
event_bus = EventBus()


# Standard event names:
class EventNames:
    """Standard event names used in the application."""
    TAG_DETECTED = "tag_detected"                # Parameters: tag_uid (str)
    PLAYBACK_STARTED = "playback_started"        # Parameters: media_id (str), tag_uid (str, optional)
    PLAYBACK_STOPPED = "playback_stopped"        # Parameters: media_id (str), position (int)
    PLAYBACK_PAUSED = "playback_paused"          # Parameters: media_id (str), position (int)
    PLAYBACK_RESUMED = "playback_resumed"        # Parameters: media_id (str), position (int)
    MEDIA_ADDED = "media_added"                  # Parameters: media_id (str), metadata (dict)
    MEDIA_REMOVED = "media_removed"              # Parameters: media_id (str)
    BLUETOOTH_CONNECTED = "bluetooth_connected"  # Parameters: device_address (str), device_name (str)
    BLUETOOTH_DISCONNECTED = "bluetooth_disconnected"  # Parameters: device_address (str)
    SYSTEM_ERROR = "system_error"                # Parameters: error_type (str), message (str), details (dict)
    SYSTEM_STARTUP = "system_startup"            # Parameters: None
    SYSTEM_SHUTDOWN = "system_shutdown"          # Parameters: None
