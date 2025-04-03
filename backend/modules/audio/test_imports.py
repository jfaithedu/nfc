#!/usr/bin/env python3
"""
Test script to check if GObject and other required modules can be imported.
"""

print("Testing imports...")

try:
    import gi
    print("✓ gi module imported successfully")
    
    # Try to import GLib
    gi.require_version('Gst', '1.0')
    from gi.repository import GLib, Gst
    print("✓ GLib and Gst modules imported successfully")
    
    # Try to initialize GStreamer
    Gst.init(None)
    print("✓ GStreamer initialized successfully")
    
    # Try to import dbus
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    print("✓ dbus modules imported successfully")
    
    # Try to create a main loop
    DBusGMainLoop(set_as_default=True)
    main_loop = GLib.MainLoop()
    print("✓ GLib main loop created successfully")
    
    print("\nAll modules imported successfully!")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nTroubleshooting suggestions:")
    print("1. Make sure you have the required system packages installed:")
    print("   sudo apt-get install -y python3-gi python3-gi-cairo python3-dbus gir1.2-gstreamer-1.0")
    print("2. Try installing pygobject directly in your virtual environment:")
    print("   pip install pygobject")
    print("3. If in a virtual environment, you might need to enable system packages:")
    print("   This can be done by creating a new venv with --system-site-packages")
    
except Exception as e:
    print(f"✗ Error: {e}")