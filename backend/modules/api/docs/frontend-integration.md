# NFC Music Player - Frontend Integration Guide

This guide is intended for the frontend developer who will be building the React+TypeScript admin interface for the NFC Music Player. It provides all the details you need to connect to the backend API and implement the required functionality.

## Table of Contents

- [API Overview](#api-overview)
- [Authentication](#authentication)
- [Tag Management](#tag-management)
- [Media Management](#media-management)
- [System Management](#system-management)
- [NFC Writing](#nfc-writing)
- [Error Handling](#error-handling)
- [Common Operations & Examples](#common-operations--examples)

## API Overview

The backend API is built with Flask and follows RESTful principles. All API endpoints are prefixed with `/api/` and return JSON responses.

All successful responses follow this format:

```json
{
  "success": true,
  "data": {
    // Response data here
  }
}
```

All error responses follow this format:

```json
{
  "success": false,
  "error": {
    "message": "Error message",
    "status": 400,
    "details": {
      // Optional additional details
    }
  }
}
```

## Authentication

The API uses a simple PIN-based authentication system that generates JWT tokens.

### Authentication Flow

1. User enters a PIN
2. Client sends PIN to the authentication endpoint
3. Server validates PIN and returns a JWT token
4. Client includes the JWT token in the Authorization header for all subsequent requests

### Endpoints

#### Login

```
POST /api/auth/login
```

Request body:

```json
{
  "pin": "1234"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600
  }
}
```

#### How to use the token

For all protected API endpoints, include the token in the `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Tag Management

These endpoints allow you to manage NFC tags, view their status, and associate them with media.

### Endpoints

#### Get All Tags

```
GET /api/tags
```

Response:

```json
{
  "success": true,
  "data": {
    "tags": [
      {
        "uid": "04a2b3c9",
        "name": "Bob Marley",
        "description": "Bob Marley playlist",
        "media_id": "123",
        "last_used": "2025-03-02T14:30:45"
      }
      // More tags...
    ]
  }
}
```

#### Get Specific Tag

```
GET /api/tags/{tag_uid}
```

Response:

```json
{
  "success": true,
  "data": {
    "tag": {
      "uid": "04a2b3c9",
      "name": "Bob Marley",
      "description": "Bob Marley playlist",
      "media_id": "123",
      "last_used": "2025-03-02T14:30:45"
    }
  }
}
```

#### Create New Tag

```
POST /api/tags
```

Request body:

```json
{
  "uid": "04a2b3c9",
  "name": "Bob Marley",
  "description": "Bob Marley playlist",
  "media_id": "123" // Optional
}
```

#### Update Tag

```
PUT /api/tags/{tag_uid}
```

Request body:

```json
{
  "name": "Bob Marley Greatest Hits",
  "description": "Updated description",
  "media_id": "456"
}
```

#### Delete Tag

```
DELETE /api/tags/{tag_uid}
```

#### Associate Tag with Media

```
POST /api/tags/{tag_uid}/associate
```

Request body:

```json
{
  "media_id": "456"
}
```

#### Get Last Detected Tag

```
GET /api/tags/last-detected
```

#### Get Tag Usage History

```
GET /api/tags/history?limit=10&offset=0
```

## Media Management

These endpoints allow you to manage media sources, upload files, and control playback.

### Endpoints

#### Get All Media

```
GET /api/media?limit=20&offset=0
```

Response:

```json
{
  "success": true,
  "data": {
    "media": [
      {
        "id": "123",
        "title": "Bob Marley - No Woman No Cry",
        "description": "Live version",
        "source_url": "https://www.youtube.com/watch?v=x59kS2AOrGM",
        "media_type": "youtube",
        "created_at": "2025-03-01T10:15:30",
        "cached": true
      }
      // More media items...
    ],
    "pagination": {
      "total": 42,
      "limit": 20,
      "offset": 0
    }
  }
}
```

#### Get Specific Media

```
GET /api/media/{media_id}
```

Response includes associated tags and cache status.

#### Add YouTube Media

```
POST /api/media/youtube
```

Request body:

```json
{
  "url": "https://www.youtube.com/watch?v=x59kS2AOrGM",
  "title": "Bob Marley - No Woman No Cry", // Optional
  "description": "Live version", // Optional
  "cache": true // Optional, downloads media for offline use
}
```

#### Upload Local Media

```
POST /api/media/upload
```

This is a multipart form upload:

- `file`: The media file (must be one of the allowed formats)
- `title`: (Optional) Title for the media
- `description`: (Optional) Description

#### Delete Media

```
DELETE /api/media/{media_id}
```

#### Test Playback

```
POST /api/media/{media_id}/test
```

Plays the media on the Raspberry Pi's connected speaker.

#### Stop Playback

```
POST /api/media/playback/stop
```

#### Download Media

```
GET /api/media/{media_id}/download
```

Returns the media file as an attachment.

#### Get Cache Status

```
GET /api/media/cache/status
```

#### Clean Cache

```
POST /api/media/cache/clean
```

Request body:

```json
{
  "force": false // Optional, force clean even if below threshold
}
```

## System Management

These endpoints allow you to view and manage system settings, Bluetooth connections, and perform system operations.

### Endpoints

#### Get System Status

```
GET /api/system/status
```

Returns comprehensive system status including component status, hardware info, and statistics.

#### Get Bluetooth Devices

```
GET /api/system/bluetooth/devices
```

Response:

```json
{
  "success": true,
  "data": {
    "devices": [
      {
        "address": "00:11:22:33:44:55",
        "name": "JBL Flip 5",
        "paired": true,
        "trusted": true,
        "connected": false,
        "icon": "audio-card",
        "rssi": -58,
        "audio_sink": true
      }
      // More devices...
    ],
    "current_device": {
      "address": "AA:BB:CC:DD:EE:FF",
      "name": "Bose SoundLink",
      "connected": true
    }
  }
}
```

#### Pair with Bluetooth Device

```
POST /api/system/bluetooth/pair
```

Request body:

```json
{
  "address": "00:11:22:33:44:55"
}
```

This endpoint establishes a pairing relationship (trusted connection) with a Bluetooth device without actually connecting to it.

#### Connect to Paired Bluetooth Device

```
POST /api/system/bluetooth/connect
```

Request body:

```json
{
  "address": "00:11:22:33:44:55",
  "auto_pair": true // Optional, default is true. If true, will attempt to pair if not already paired
}
```

This endpoint connects to a previously paired Bluetooth device or attempts to pair and connect if auto_pair is true.

#### Disconnect Bluetooth Device

```
POST /api/system/bluetooth/disconnect
```

#### Set Volume

```
POST /api/system/volume
```

Request body:

```json
{
  "volume": 75 // 0-100
}
```

#### Get System Settings

```
GET /api/system/settings
```

Returns a filtered view of system settings.

#### Update System Settings

```
PUT /api/system/settings
```

Request body can include various settings. For sensitive settings, include the admin PIN in the `X-Admin-PIN` header.

#### Change Admin PIN

```
POST /api/system/change_pin
```

Request body:

```json
{
  "current_pin": "1234",
  "new_pin": "5678"
}
```

#### Create Backup

```
POST /api/system/backup
```

Returns a ZIP file with system backup.

#### Restore from Backup

```
POST /api/system/restore
```

Multipart form upload:

- `backup_file`: The backup ZIP file
- `pin`: Admin PIN

#### Restart System

```
POST /api/system/restart
```

Request body:

```json
{
  "pin": "1234"
}
```

## NFC Writing

These endpoints allow you to write data to NFC tags.

### Endpoints

#### Start Write Mode

```
POST /api/nfc/write/start
```

Request body:

```json
{
  "timeout": 60, // Optional, seconds to remain in write mode
  "data": "...", // Optional, data to write
  "tag_uid": "04a2b3c9" // Optional, specific tag to target
}
```

#### Stop Write Mode

```
POST /api/nfc/write/stop
```

#### Get Write Status

```
GET /api/nfc/write/status
```

#### Write to Specific Tag

```
POST /api/nfc/write/{tag_uid}
```

Request body:

```json
{
  "data": "..." // Data to write
}
```

#### Read Raw Tag Data

```
GET /api/nfc/read
```

#### Read NDEF Data

```
GET /api/nfc/ndef/read
```

#### Write NDEF Data

```
POST /api/nfc/ndef/write
```

Request body:

```json
{
  "url": "https://www.youtube.com/watch?v=x59kS2AOrGM", // Optional
  "text": "Bob Marley - No Woman No Cry" // Optional
}
```

At least one of `url` or `text` must be provided.

## Error Handling

The API returns appropriate HTTP status codes and structured error responses:

- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required or invalid
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

Example error response:

```json
{
  "success": false,
  "error": {
    "message": "Tag with UID 04a2b3c9 not found",
    "status": 404
  }
}
```

Handle these errors appropriately in your frontend code, displaying user-friendly messages and implementing retry mechanisms where appropriate.

## Common Operations & Examples

### Typical User Flow for Adding a New NFC Tag

1. Add media source:

```javascript
// Add YouTube video
const addMedia = async (url) => {
  const response = await fetch("/api/media/youtube", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      url,
      cache: true,
    }),
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  return result.data.media;
};

// Example usage
const media = await addMedia("https://www.youtube.com/watch?v=x59kS2AOrGM");
console.log(`Added media with ID: ${media.id}`);
```

2. Scan for NFC tag and create it:

```javascript
// Start a loop that checks for the last detected tag
const waitForTag = async () => {
  let detected = false;
  let tag = null;

  while (!detected) {
    const response = await fetch("/api/tags/last-detected", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const result = await response.json();
    if (result.success && result.data.last_detected.uid) {
      detected = true;
      tag = result.data.last_detected;
      console.log(`Detected tag: ${tag.uid}`);
    }

    // Wait before checking again
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  return tag;
};

// Example usage
alert("Please place the NFC tag on the reader...");
const detectedTag = await waitForTag();
```

3. Associate tag with media:

```javascript
const associateTagWithMedia = async (tagUid, mediaId) => {
  const response = await fetch(`/api/tags/${tagUid}/associate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      media_id: mediaId,
    }),
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  return result.data;
};

// Example usage
await associateTagWithMedia(detectedTag.uid, media.id);
alert("Tag successfully associated with media!");
```

### Bluetooth Pairing and Connection Flow

The system now uses BlueALSA for Bluetooth audio management, which provides better stability and compatibility with most Bluetooth speakers. The API clearly separates the **pairing** process (establishing a trusted relationship with a device) and the **connection** process (actively connecting to use the device).

Here's an example of how to discover, pair with, and connect to a Bluetooth device:

```javascript
// 1. Discover available Bluetooth devices
const discoverDevices = async () => {
  const response = await fetch("/api/system/bluetooth/devices", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  // Filter for devices that support audio (A2DP sink)
  const audioDevices = result.data.devices.filter(
    (device) => device.audio_sink
  );
  return audioDevices;
};

// 2. Pair with a Bluetooth device
const pairDevice = async (address) => {
  const response = await fetch("/api/system/bluetooth/pair", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      address,
    }),
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  return result.data;
};

// 3. Connect to a paired device
const connectToDevice = async (address) => {
  const response = await fetch("/api/system/bluetooth/connect", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      address,
      auto_pair: false, // We already paired explicitly
    }),
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  return result.data;
};

// Example usage in a React component
const connectBluetoothSpeaker = async () => {
  try {
    // First discover devices
    setStatus("Discovering devices...");
    const devices = await discoverDevices();

    // Let user select a device (simplified example - would use UI components in real app)
    setStatus("Select a device to pair with");
    const selectedDevice = devices[0]; // In a real app, user would select from a list

    // Pair with the device
    setStatus(`Pairing with ${selectedDevice.name}...`);
    await pairDevice(selectedDevice.address);

    // Connect to the device
    setStatus(`Connecting to ${selectedDevice.name}...`);
    const result = await connectToDevice(selectedDevice.address);

    setStatus(`Connected to ${result.device.name}`);
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  }
};
```

This separation of pairing and connecting gives you more control over the Bluetooth connection process and allows for more robust error handling. You can also build a UI that clearly distinguishes between:

1. **Available devices** - Devices that are in range but not paired
2. **Paired devices** - Devices that have an established trusted relationship but are not currently connected
3. **Connected device** - The currently active Bluetooth audio device

Note that the device objects now include additional properties such as `audio_sink` (indicates A2DP sink support), `trusted`, `icon`, and `rssi` (signal strength) which you can use to enhance your UI.

### Writing NDEF Data to a Tag

```javascript
const writeNdefUrl = async (url) => {
  alert("Place the tag on the reader to write the URL...");

  const response = await fetch("/api/nfc/ndef/write", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      url,
    }),
  });

  const result = await response.json();
  if (!result.success) {
    throw new Error(result.error.message);
  }

  return result.data;
};

// Example usage
try {
  await writeNdefUrl("https://www.youtube.com/watch?v=x59kS2AOrGM");
  alert("URL successfully written to tag!");
} catch (error) {
  alert(`Error writing to tag: ${error.message}`);
}
```

## Recommended Development Tools

- [React Query](https://tanstack.com/query/latest) for data fetching and caching
- [Axios](https://axios-http.com/) for HTTP requests (optional, fetch also works well)
- [React Hook Form](https://react-hook-form.com/) for form handling
- [Zod](https://zod.dev/) for request/response validation

## BlueALSA Implementation Notes

The system now uses BlueALSA for Bluetooth audio management instead of the previously used bluez-alsa compiled from source. This change brings several improvements:

- **Simplified Installation**: Uses standard Raspberry Pi OS packages
- **Better Stability**: Direct ALSA to BlueALSA routing
- **Improved Compatibility**: Works with a wider range of Bluetooth speakers

### Important: Separation of Pairing and Connecting

The most critical change in the new Bluetooth system is the clear separation between:

1. **Pairing** (`/api/system/bluetooth/pair`): Establishes a trusted relationship with a device without connecting to it. This is a one-time operation that makes the device "known" to the system.

2. **Connecting** (`/api/system/bluetooth/connect`): Establishes an active connection to an already paired device. This is what you do each time you want to use the device.

This separation gives you:

- More precise control over the Bluetooth lifecycle
- Better error handling (you can detect exactly where an issue occurs)
- Improved UI possibilities (showing different states for paired vs. connected devices)
- More reliable connections, especially for audio devices

Your frontend should reflect this separation clearly in both the UI design and the implementation logic. For devices that require a PIN, the pairing process will handle this authentication, while the connection process focuses only on establishing the A2DP audio profile.

## Testing the API

During development, you can test the API endpoints using tools like:

1. [Postman](https://www.postman.com/)
2. [Insomnia](https://insomnia.rest/)
3. [curl](https://curl.se/) from the command line

Example curl command to test authentication:

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"pin": "1234"}'
```

## Development Workflow Tips

1. Start by implementing the authentication flow
2. Then build the basic tag and media management screens
3. Add more complex features like NFC writing and Bluetooth management
4. Implement system settings and backup/restore features last
5. Test thoroughly on the actual hardware throughout development

Remember that the API is designed to be local-only, so your React app will be served from the same origin as the API (http://localhost:5000).

## API Health Check

The API provides a simple health check endpoint at `/api/health` that you can use to verify the API is up and running.

```javascript
const checkApiHealth = async () => {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    console.log(`API is healthy! Uptime: ${data.uptime} seconds`);
    return true;
  } catch (error) {
    console.error("API health check failed:", error);
    return false;
  }
};
```

This will be useful during development to ensure your local setup is working correctly.
