# NDEF API Implementation Guide

This document provides implementation details for adding NDEF (NFC Data Exchange Format) support to the API.

## Overview

NDEF is a standardized data format used for NFC tags. The implementation will provide two main endpoints:

1. Reading NDEF data from a detected tag
2. Writing NDEF data to a detected tag

## API Endpoints Implementation

When implementing the `routes/nfc_writer.py` file, add the following route handlers:

```python
@app.route('/api/nfc/ndef/read', methods=['GET'])
@require_auth
def read_ndef_data():
    """Read and parse NDEF formatted data from a detected tag."""
    try:
        # Check if a tag is detected first
        tag_uid = nfc_controller.poll_for_tag()
        if not tag_uid:
            return api_error_response("No NFC tag detected", 404)

        # Read NDEF data
        ndef_data = nfc_controller.read_ndef_data()

        if ndef_data is None:
            return jsonify({
                "success": True,
                "data": {
                    "message": "No NDEF data found on tag",
                    "tag_uid": tag_uid,
                    "ndef_data": None
                }
            })

        # Return the parsed NDEF data
        return jsonify({
            "success": True,
            "data": {
                "tag_uid": tag_uid,
                "ndef_data": ndef_data
            }
        })

    except NFCNoTagError:
        return api_error_response("No NFC tag detected", 404)
    except NFCReadError as e:
        return api_error_response(f"Error reading NDEF data: {str(e)}", 500)
    except Exception as e:
        logger.error(f"Unexpected error reading NDEF data: {str(e)}")
        return api_error_response("Internal server error", 500, {"error": str(e)})


@app.route('/api/nfc/ndef/write', methods=['POST'])
@require_auth
def write_ndef_data():
    """
    Write NDEF formatted data to a detected tag.

    Request body should include either url or text or both:
    {
        "url": "https://example.com",
        "text": "Example text"
    }
    """
    try:
        # Validate the request body
        data = request.get_json()
        if not data:
            return api_error_response("Request body is required", 400)

        url = data.get('url')
        text = data.get('text')

        if not url and not text:
            return api_error_response("Either 'url' or 'text' must be provided", 400)

        # Check if a tag is detected
        tag_uid = nfc_controller.poll_for_tag()
        if not tag_uid:
            return api_error_response("No NFC tag detected", 404)

        # Write NDEF data to the tag
        success = nfc_controller.write_ndef_data(url=url, text=text)

        return jsonify({
            "success": True,
            "data": {
                "message": "NDEF data written successfully",
                "tag_uid": tag_uid,
                "content": {
                    "url": url,
                    "text": text
                }
            }
        })

    except NFCNoTagError:
        return api_error_response("No NFC tag detected", 404)
    except NFCWriteError as e:
        return api_error_response(f"Error writing NDEF data: {str(e)}", 500)
    except ValueError as e:
        return api_error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Unexpected error writing NDEF data: {str(e)}")
        return api_error_response("Internal server error", 500, {"error": str(e)})
```

## Required Imports

Ensure you have the following imports at the top of your file:

```python
from flask import jsonify, request
from modules.nfc import nfc_controller
from modules.nfc.exceptions import NFCNoTagError, NFCReadError, NFCWriteError
from ..middleware.auth import require_auth
from ..middleware.error_handler import api_error_response
import logging

# Create logger
logger = logging.getLogger(__name__)
```

## Testing the API

You can test the new endpoints with curl:

### Reading NDEF Data

```bash
curl -X GET http://localhost:5000/api/nfc/ndef/read \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

### Writing NDEF Data

```bash
curl -X POST http://localhost:5000/api/nfc/ndef/write \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -d '{"url": "https://example.com", "text": "Example text"}'
```

## Integration with Frontend

When integrating with the frontend, add the following API client methods:

```javascript
// Read NDEF data from a tag
async function readNdefData() {
  const response = await fetch("/api/nfc/ndef/read", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${getAuthToken()}`,
    },
  });
  return await response.json();
}

// Write NDEF data to a tag
async function writeNdefData(url, text) {
  const response = await fetch("/api/nfc/ndef/write", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getAuthToken()}`,
    },
    body: JSON.stringify({
      url,
      text,
    }),
  });
  return await response.json();
}
```

## Error Handling

Both endpoints handle the following error cases:

- No tag detected (404)
- Reading/writing errors (500)
- Invalid request data (400)
- Authentication errors (handled by the @require_auth decorator)

These endpoints should be thoroughly tested with various tag types, especially with the NTAG215 tags which have specialized handling in the NFC controller code.
