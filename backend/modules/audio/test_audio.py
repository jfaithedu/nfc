#!/usr/bin/env python3
"""
Test suite for the audio module.

Tests the functionality of the audio module components:
- Bluetooth manager
- Audio playback
- System sounds
- Audio controller
"""

import os
import time
import unittest
from unittest.mock import patch, MagicMock, ANY
import tempfile
from pathlib import Path
import json

# Import module to test
import backend.modules.audio as audio
from backend.modules.audio.bluetooth_manager import BluetoothManager
from backend.modules.audio.playback_handler import AudioPlayer
from backend.modules.audio.exceptions import (
    AudioError,
    BluetoothDiscoveryError,
    BluetoothConnectionError,
    MediaLoadError
)

# Constants for testing
TEST_SOUND_FILE = "test_sound.wav"
TEST_MEDIA_FILE = "test_media.mp3"
TEST_DEVICE_ADDRESS = "00:11:22:33:44:55"
TEST_DEVICE_NAME = "Test Speaker"

class MockDBusInterface:
    """Mock for D-Bus interface."""
    
    def __init__(self, *args, **kwargs):
        self.calls = []
    
    def __call__(self, *args, **kwargs):
        self.calls.append(('call', args, kwargs))
        return self
    
    def Get(self, *args, **kwargs):
        self.calls.append(('Get', args, kwargs))
        
        # Return appropriate values based on what's being requested
        if args[0] == "org.bluez.Adapter1" and args[1] == "Powered":
            return True
        if args[0] == "org.bluez.Device1" and args[1] == "Connected":
            return True
        if args[0] == "org.bluez.Device1" and args[1] == "Trusted":
            return True
        
        return None
    
    def Set(self, *args, **kwargs):
        self.calls.append(('Set', args, kwargs))
        return None
    
    def GetAll(self, *args, **kwargs):
        self.calls.append(('GetAll', args, kwargs))
        
        # Return fake device properties
        if args[0] == "org.bluez.Device1":
            return {
                "Name": TEST_DEVICE_NAME,
                "Address": TEST_DEVICE_ADDRESS,
                "Paired": True,
                "Trusted": True,
                "Connected": True,
                "UUIDs": ["0000110b-0000-1000-8000-00805f9b34fb"]  # A2DP Sink
            }
        
        return {}
    
    def StartDiscovery(self, *args, **kwargs):
        self.calls.append(('StartDiscovery', args, kwargs))
        return None
    
    def StopDiscovery(self, *args, **kwargs):
        self.calls.append(('StopDiscovery', args, kwargs))
        return None
    
    def Connect(self, *args, **kwargs):
        self.calls.append(('Connect', args, kwargs))
        return None
    
    def Disconnect(self, *args, **kwargs):
        self.calls.append(('Disconnect', args, kwargs))
        return None
    
    def GetManagedObjects(self, *args, **kwargs):
        self.calls.append(('GetManagedObjects', args, kwargs))
        
        # Return a fake adapter and device
        return {
            "/org/bluez/hci0": {
                "org.bluez.Adapter1": {}
            },
            "/org/bluez/hci0/dev_00_11_22_33_44_55": {
                "org.bluez.Device1": {}
            }
        }


class MockGst:
    """Mock for GStreamer."""
    
    def __init__(self):
        self.State = MagicMock()
        self.State.PLAYING = 1
        self.State.PAUSED = 2
        self.State.NULL = 0
        
        self.StateChangeReturn = MagicMock()
        self.StateChangeReturn.SUCCESS = 1
        self.StateChangeReturn.FAILURE = 0
        
        self.Format = MagicMock()
        self.Format.TIME = 1
        
        self.SECOND = 1000000000  # nanoseconds
        
        self.SeekFlags = MagicMock()
        self.SeekFlags.FLUSH = 1
        self.SeekFlags.KEY_UNIT = 2
        
        self.MessageType = MagicMock()
        self.MessageType.ERROR = 1
        self.MessageType.EOS = 2
        self.MessageType.STATE_CHANGED = 3

    def init(self, *args):
        pass
    
    def Pipeline(self):
        return MagicMock()
    
    def ElementFactory(self):
        return MagicMock()


class TestBluetoothManager(unittest.TestCase):
    """Tests for the BluetoothManager class."""
    
    @patch('backend.modules.audio.bluetooth_manager.dbus')
    @patch('backend.modules.audio.bluetooth_manager.GLib')
    def setUp(self, mock_glib, mock_dbus):
        """Set up the test environment."""
        # Mock D-Bus related objects
        self.mock_dbus = mock_dbus
        self.mock_dbus.Interface.return_value = MockDBusInterface()
        self.mock_dbus.SystemBus.return_value = MagicMock()
        
        # Create temporary directory for config
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Initialize BluetoothManager with patches
        with patch('backend.modules.audio.bluetooth_manager.Path.home') as mock_home:
            mock_home.return_value = Path(self.temp_dir.name)
            self.bluetooth_manager = BluetoothManager()
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_initialization(self):
        """Test initialization of BluetoothManager."""
        self.assertIsNotNone(self.bluetooth_manager._adapter)
        self.assertIsNotNone(self.bluetooth_manager._adapter_path)
        self.assertFalse(self.bluetooth_manager._discovering)
        self.assertEqual(self.bluetooth_manager._discovered_devices, {})
    
    @patch('backend.modules.audio.bluetooth_manager.time')
    def test_start_discovery(self, mock_time):
        """Test starting Bluetooth discovery."""
        result = self.bluetooth_manager.start_discovery(timeout=5)
        self.assertTrue(result)
        self.assertTrue(self.bluetooth_manager._discovering)
    
    def test_stop_discovery(self):
        """Test stopping Bluetooth discovery."""
        # First start discovery
        self.bluetooth_manager.start_discovery()
        self.assertTrue(self.bluetooth_manager._discovering)
        
        # Then stop it
        result = self.bluetooth_manager.stop_discovery()
        self.assertTrue(result)
        self.assertFalse(self.bluetooth_manager._discovering)
    
    @patch('backend.modules.audio.bluetooth_manager.time')
    def test_connect_device(self, mock_time):
        """Test connecting to a Bluetooth device."""
        # Add a fake discovered device
        self.bluetooth_manager._discovered_devices = {
            "/org/bluez/hci0/dev_00_11_22_33_44_55": {
                "name": TEST_DEVICE_NAME,
                "address": TEST_DEVICE_ADDRESS,
                "path": "/org/bluez/hci0/dev_00_11_22_33_44_55",
                "paired": False,
                "trusted": False,
                "connected": False
            }
        }
        
        # Test connection
        result = self.bluetooth_manager.connect_device(TEST_DEVICE_ADDRESS)
        self.assertTrue(result)
        self.assertIsNotNone(self.bluetooth_manager._connected_device)
        self.assertEqual(
            self.bluetooth_manager._connected_device["address"], 
            TEST_DEVICE_ADDRESS
        )
    
    def test_disconnect_device(self):
        """Test disconnecting from a Bluetooth device."""
        # Setup a connected device
        self.bluetooth_manager._connected_device = {
            "name": TEST_DEVICE_NAME,
            "address": TEST_DEVICE_ADDRESS,
            "path": "/org/bluez/hci0/dev_00_11_22_33_44_55",
            "paired": True,
            "trusted": True,
            "connected": True
        }
        
        # Test disconnection
        result = self.bluetooth_manager.disconnect_device()
        self.assertTrue(result)
        self.assertIsNone(self.bluetooth_manager._connected_device)
    
    def test_get_discovered_devices(self):
        """Test getting discovered devices."""
        # Add a fake discovered device
        fake_device = {
            "name": TEST_DEVICE_NAME,
            "address": TEST_DEVICE_ADDRESS,
            "path": "/org/bluez/hci0/dev_00_11_22_33_44_55",
            "paired": False,
            "trusted": False,
            "connected": False
        }
        self.bluetooth_manager._discovered_devices = {
            "/org/bluez/hci0/dev_00_11_22_33_44_55": fake_device
        }
        
        # Test getting devices
        devices = self.bluetooth_manager.get_discovered_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0], fake_device)
    
    def test_save_paired_device(self):
        """Test saving a paired device."""
        result = self.bluetooth_manager.save_paired_device(
            TEST_DEVICE_ADDRESS, TEST_DEVICE_NAME
        )
        self.assertTrue(result)
        
        # Check that the device was saved
        saved_devices = self.bluetooth_manager.get_saved_devices()
        self.assertEqual(len(saved_devices), 1)
        self.assertEqual(saved_devices[0]["address"], TEST_DEVICE_ADDRESS)
        self.assertEqual(saved_devices[0]["name"], TEST_DEVICE_NAME)


class TestAudioPlayer(unittest.TestCase):
    """Tests for the AudioPlayer class."""
    
    @patch('backend.modules.audio.playback_handler.gi')
    @patch('backend.modules.audio.playback_handler.Gst')
    @patch('backend.modules.audio.playback_handler.GLib')
    def setUp(self, mock_glib, mock_gst, mock_gi):
        """Set up the test environment."""
        # Create mock for GStreamer pipeline and elements
        self.mock_gst = mock_gst
        self.mock_gst.Pipeline.new.return_value = MagicMock()
        self.mock_gst.ElementFactory.make.return_value = MagicMock()
        
        # Setup query returns for position and duration
        pipeline_mock = self.mock_gst.Pipeline.new.return_value
        pipeline_mock.query_position.return_value = (True, 5 * 1000000000)  # 5 seconds
        pipeline_mock.query_duration.return_value = (True, 60 * 1000000000)  # 60 seconds
        pipeline_mock.set_state.return_value = self.mock_gst.StateChangeReturn.SUCCESS
        
        # Initialize AudioPlayer
        self.audio_player = AudioPlayer()
        
        # Create a temporary test file
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = os.path.join(self.temp_dir.name, TEST_MEDIA_FILE)
        with open(self.test_file, 'w') as f:
            f.write("Test media content")
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    @patch('backend.modules.audio.playback_handler.os.path.exists')
    def test_load_media(self, mock_exists):
        """Test loading media."""
        mock_exists.return_value = True
        
        # Test loading media
        result = self.audio_player.load_media(self.test_file)
        self.assertTrue(result)
        self.assertEqual(self.audio_player._current_media, self.test_file)
    
    def test_play(self):
        """Test playing media."""
        # First load media
        with patch('backend.modules.audio.playback_handler.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.audio_player.load_media(self.test_file)
        
        # Test play
        result = self.audio_player.play()
        self.assertTrue(result)
        self.assertEqual(self.audio_player._state, 'playing')
    
    def test_pause(self):
        """Test pausing playback."""
        # Setup playing state
        with patch('backend.modules.audio.playback_handler.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.audio_player.load_media(self.test_file)
            self.audio_player.play()
        
        # Override state for testing
        self.audio_player._state = 'playing'
        
        # Test pause
        result = self.audio_player.pause()
        self.assertTrue(result)
        self.assertEqual(self.audio_player._state, 'paused')
    
    def test_resume(self):
        """Test resuming playback."""
        # Setup paused state
        with patch('backend.modules.audio.playback_handler.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.audio_player.load_media(self.test_file)
            self.audio_player._state = 'paused'
        
        # Test resume
        result = self.audio_player.resume()
        self.assertTrue(result)
        self.assertEqual(self.audio_player._state, 'playing')
    
    def test_stop(self):
        """Test stopping playback."""
        # Setup playing state
        with patch('backend.modules.audio.playback_handler.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.audio_player.load_media(self.test_file)
            self.audio_player.play()
        
        # Test stop
        result = self.audio_player.stop()
        self.assertTrue(result)
        self.assertEqual(self.audio_player._state, 'stopped')
    
    def test_seek(self):
        """Test seeking in media."""
        # Setup playing state
        with patch('backend.modules.audio.playback_handler.os.path.exists') as mock_exists:
            mock_exists.return_value = True
            self.audio_player.load_media(self.test_file)
            self.audio_player.play()
        
        # Test seek
        result = self.audio_player.seek(30)  # Seek to 30 seconds
        self.assertTrue(result)
    
    def test_volume_control(self):
        """Test volume control."""
        # Test setting volume
        new_volume = self.audio_player.set_volume(75)
        self.assertEqual(new_volume, 75)
        
        # Test getting volume
        volume = self.audio_player.get_volume()
        self.assertEqual(volume, 75)
    
    def test_mute_unmute(self):
        """Test muting and unmuting."""
        # Set initial volume
        self.audio_player.set_volume(80)
        
        # Test mute
        result = self.audio_player.mute()
        self.assertTrue(result)
        self.assertTrue(self.audio_player._muted)
        self.assertEqual(self.audio_player.get_volume(), 0)
        
        # Test unmute
        result = self.audio_player.unmute()
        self.assertTrue(result)
        self.assertFalse(self.audio_player._muted)
        self.assertEqual(self.audio_player.get_volume(), 80)


class TestSystemSounds(unittest.TestCase):
    """Tests for the system_sounds module."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create temporary directory for sounds
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sounds_dir = Path(self.temp_dir.name)
        
        # Create test sound files
        for sound_type in ['error', 'success', 'info', 'warning']:
            sound_file = self.sounds_dir / f"{sound_type}.wav"
            with open(sound_file, 'w') as f:
                f.write(f"Test {sound_type} sound content")
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    @patch('backend.modules.audio.system_sounds.subprocess.run')
    def test_initialize_and_play(self, mock_run):
        """Test initializing and playing system sounds."""
        from backend.modules.audio.system_sounds import initialize_system_sounds, play_sound
        
        # Test initialization
        result = initialize_system_sounds(self.sounds_dir)
        self.assertTrue(result)
        
        # Test playing a sound
        result = play_sound('error', blocking=True)
        self.assertTrue(result)
        mock_run.assert_called_once()
    
    @patch('backend.modules.audio.system_sounds._sounds')
    def test_get_available_sounds(self, mock_sounds):
        """Test getting available sounds."""
        from backend.modules.audio.system_sounds import get_available_sounds
        
        # Set up mock sounds
        mock_sounds.keys.return_value = ['error', 'success']
        
        # Test getting available sounds
        sounds = get_available_sounds()
        self.assertEqual(set(sounds), set(['error', 'success']))
    
    @patch('backend.modules.audio.system_sounds._sounds', {})
    def test_add_custom_sound(self):
        """Test adding a custom sound."""
        from backend.modules.audio.system_sounds import add_custom_sound
        
        # Create test sound file
        custom_sound = self.sounds_dir / "custom.wav"
        with open(custom_sound, 'w') as f:
            f.write("Custom sound content")
        
        # Test adding custom sound
        result = add_custom_sound('custom', str(custom_sound))
        self.assertTrue(result)
        
        # Verify it's in the sounds dictionary
        from backend.modules.audio.system_sounds import _sounds
        self.assertIn('custom', _sounds)


class TestAudioController(unittest.TestCase):
    """Tests for the audio_controller module."""
    
    @patch('backend.modules.audio.audio_controller.BluetoothManager')
    @patch('backend.modules.audio.audio_controller.AudioPlayer')
    @patch('backend.modules.audio.audio_controller.initialize_system_sounds')
    def setUp(self, mock_init_sounds, mock_audio_player, mock_bt_manager):
        """Set up the test environment."""
        # Set up mocks
        self.mock_bt_manager = mock_bt_manager.return_value
        self.mock_audio_player = mock_audio_player.return_value
        self.mock_init_sounds = mock_init_sounds
        
        # Mock saved devices
        self.mock_bt_manager.get_saved_devices.return_value = [
            {
                'name': TEST_DEVICE_NAME,
                'address': TEST_DEVICE_ADDRESS,
                'last_connected': time.time()
            }
        ]
        
        # Import and initialize audio controller
        import backend.modules.audio.audio_controller as controller
        controller._initialized = False
        self.controller = controller
        self.controller.initialize()
    
    def test_play_functions(self):
        """Test playback control functions."""
        # Test play
        self.controller.play(TEST_MEDIA_FILE)
        self.mock_audio_player.load_media.assert_called_once_with(TEST_MEDIA_FILE)
        self.mock_audio_player.play.assert_called_once()
        
        # Test pause
        self.controller.pause()
        self.mock_audio_player.pause.assert_called_once()
        
        # Test resume
        self.controller.resume()
        self.mock_audio_player.resume.assert_called_once()
        
        # Test stop
        self.controller.stop()
        self.mock_audio_player.stop.assert_called_once()
        
        # Test seek
        self.controller.seek(30)
        self.mock_audio_player.seek.assert_called_once_with(30)
    
    def test_volume_functions(self):
        """Test volume control functions."""
        # Test set volume
        self.controller.set_volume(75)
        self.mock_audio_player.set_volume.assert_called_once_with(75)
        
        # Test get volume
        self.controller.get_volume()
        self.mock_audio_player.get_volume.assert_called_once()
        
        # Test mute
        self.controller.mute()
        self.mock_audio_player.mute.assert_called_once()
        
        # Test unmute
        self.controller.unmute()
        self.mock_audio_player.unmute.assert_called_once()
    
    def test_bluetooth_functions(self):
        """Test Bluetooth control functions."""
        # Test start discovery
        self.controller.start_bluetooth_discovery(timeout=15)
        self.mock_bt_manager.start_discovery.assert_called_once_with(timeout=15)
        
        # Test stop discovery
        self.controller.stop_bluetooth_discovery()
        self.mock_bt_manager.stop_discovery.assert_called_once()
        
        # Test get discovered devices
        self.controller.get_discovered_bluetooth_devices()
        self.mock_bt_manager.get_discovered_devices.assert_called_once()
        
        # Test connect device
        self.controller.connect_bluetooth_device(TEST_DEVICE_ADDRESS)
        self.mock_bt_manager.connect_device.assert_called_once_with(TEST_DEVICE_ADDRESS)
        
        # Test disconnect device
        self.controller.disconnect_bluetooth_device()
        self.mock_bt_manager.disconnect_device.assert_called_once()
        
        # Test get connected device
        self.controller.get_connected_bluetooth_device()
        self.mock_bt_manager.get_connected_device.assert_called_once()
        
        # Test get saved devices
        self.controller.get_saved_bluetooth_devices()
        self.mock_bt_manager.get_saved_devices.assert_called()
    
    def test_system_sound_functions(self):
        """Test system sound functions."""
        # Patch the play_sound function
        with patch('backend.modules.audio.audio_controller.play_sound') as mock_play:
            # Test play system sound
            self.controller.play_system_sound('error')
            mock_play.assert_called_once_with('error')
            
            # Test play error sound
            mock_play.reset_mock()
            self.controller.play_error_sound()
            mock_play.assert_called_once_with('error')
            
            # Test play success sound
            mock_play.reset_mock()
            self.controller.play_success_sound()
            mock_play.assert_called_once_with('success')
    
    def test_shutdown(self):
        """Test shutdown functionality."""
        self.controller.shutdown()
        self.mock_audio_player.stop.assert_called_once()
        self.mock_bt_manager.disconnect_device.assert_called_once()
        self.assertFalse(self.controller._initialized)
    
    def test_get_playback_status(self):
        """Test getting playback status."""
        # Setup audio player mocks
        self.mock_audio_player.get_state.return_value = 'playing'
        self.mock_audio_player.get_position.return_value = 15.5
        self.mock_audio_player.get_duration.return_value = 60.0
        
        # Set last media path
        self.controller._last_media_path = TEST_MEDIA_FILE
        
        # Test getting status
        status = self.controller.get_playback_status()
        self.assertEqual(status['state'], 'playing')
        self.assertEqual(status['position'], 15.5)
        self.assertEqual(status['duration'], 60.0)
        self.assertEqual(status['media_path'], TEST_MEDIA_FILE)


if __name__ == '__main__':
    unittest.main()
