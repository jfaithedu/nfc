# NFC Player - NDEF YouTube/Music URL Feature Implementation Guide

**Date:** 2025-03-04

**To:** Development Team
**From:** Cline (AI Assistant)
**Subject:** Implementation Plan for NDEF YouTube/Music URL Feature

## Introduction

Hello Team,

This document outlines the implementation plan for a new feature in the NFC-Based Toddler-Friendly Music Player project. The goal is to enhance the system's flexibility by allowing it to:

1.  **Read NDEF URI Records:** Detect NFC tags containing NDEF messages with YouTube or YouTube Music URLs.
2.  **Automatic Database Integration:** Automatically add detected YouTube/Music URLs to the media database if they aren't already present, potentially linking them to the tag's UID if available. This allows programming tags on other devices (like a phone) and having them work immediately with the player.
3.  **Write NDEF URI Records:** Enable the admin interface (via the backend API) to write NDEF URI records (specifically YouTube/Music URLs) onto compatible NFC tags (e.g., NTAG series).

This feature will make adding new music/playlists more seamless and leverage the standard NDEF format for better interoperability with other NFC devices.

This guide details the required changes across the backend modules. Please review the steps carefully.

---

## Implementation Details

### 1. Dependencies

- Add the `ndeflib` library for robust NDEF message parsing and creation.
  - **Action:** Add `ndeflib>=0.3.0` (or latest stable version) to `backend/requirements.txt` and `backend/modules/nfc/requirements.txt`.
  - **Action:** Ensure the library is installed in the development and deployment environments (`pip install ndeflib`).

### 2. NFC Module (`backend/modules/nfc/`)

#### 2.1. `exceptions.py`

- **Reason:** Need a specific error for when writing fails because a tag is not NDEF writable or formatted correctly.
- **Action:** Add the following exception class:
  ```python
  class NFCTagNotWritableError(NFCWriteError):
      """Exception raised when attempting to write NDEF data to a non-writable or incorrectly formatted tag."""
      pass
  ```
- **Action:** Update `backend/modules/nfc/__init__.py` to export `NFCTagNotWritableError`.

#### 2.2. `tag_processor.py`

- **Reason:** Implement reliable NDEF parsing and creation, focusing on URI records and Type 2 Tag structure.
- **Action:** Refactor `parse_ndef_data` (consider renaming to `parse_ndef_message` for clarity as per the updated README).
  - Use `ndeflib` to parse the raw NDEF message bytes read from the tag.
  - Iterate through the decoded records.
  - Specifically look for URI records (`ndeflib.uri.UriRecord`).
  - Extract the URI string from valid records.
  - Return a structured dictionary containing relevant info, e.g., `{ 'type': 'uri', 'uri': 'extracted_uri_string' }` or a list of records if multiple are found. Handle potential parsing errors gracefully.
  - Ensure it handles the raw data which might include Type 2 Tag TLV structures (the parser might need the raw message _within_ the TLV).
- **Action:** Refactor `create_ndef_data` (consider renaming to `create_ndef_uri_message`).
  - Use `ndeflib` to create a _single_ NDEF URI record (`ndeflib.uri.UriRecord(uri)`).
  - Encode this single record into an NDEF message (`ndeflib.message.encode([uri_record])`).
  - **Crucially:** Prepend the necessary Type 2 Tag TLV structure (Tag=0x03, Length, Value=NDEF Message). Calculate the length correctly (handle 1-byte vs 3-byte length field based on message size). Append the Terminator TLV (0xFE) if space allows. Pad the result with null bytes (0x00) to ensure the total length is a multiple of the tag's block/page size (usually 16 bytes for writing blocks, but NTAG pages are 4 bytes).

#### 2.3. `hardware_interface.py` (`NFCReader` class)

- **Reason:** Ensure the hardware layer can read and write the potentially multiple blocks required for NDEF messages.
- **Action:** Review `read_block` and `write_block`. The current implementation seems focused on single blocks (16 bytes) or single NTAG pages (4 bytes). NDEF messages often span multiple blocks.
  - Consider adding `read_multiple_blocks(start_block, num_blocks)` and `write_multiple_blocks(start_block, data_bytes)`. These methods would loop, calling the underlying `_pn532.ntag2xx_read_block`/`write_block` or `mifare_classic_read_block`/`write_block` for each required block/page, handling potential errors across blocks.
  - The `write_multiple_blocks` needs to be careful about tag page/block boundaries and sizes. For NTAG, it should write 4 bytes at a time to consecutive pages.
  - Alternatively, modify `read_block`/`write_block` to accept an optional `num_blocks` or `length` parameter.
- **Action:** Ensure robust error handling within these multi-block operations. If one block fails, should the whole operation fail?

#### 2.4. `nfc_controller.py`

- **Reason:** Orchestrate NDEF reading during polling and provide the NDEF writing interface.
- **Action:** Modify `poll_for_tag()`:
  - After successfully reading a `raw_uid`, attempt to read NDEF data.
  - Call a (potentially new) internal helper function `_read_and_parse_ndef()` which uses `hardware_interface` methods (like `read_multiple_blocks`) to read sufficient data starting from block 4, then uses `tag_processor.parse_ndef_message()` to parse it.
  - Return a tuple: `(formatted_uid, ndef_info)` where `ndef_info` is the parsed data (e.g., `{ 'type': 'uri', 'uri': '...' }`) or `None`.
- **Action:** Implement `write_ndef_uri(uri)`:
  - Call `tag_processor.create_ndef_uri_message(uri)` to get the fully formatted NDEF message bytes (including TLV and padding).
  - Call the appropriate `hardware_interface` method (e.g., `write_multiple_blocks`) to write these bytes starting at the standard NDEF block (usually block 4).
  - Catch potential `NFCWriteError` and the new `NFCTagNotWritableError` from the hardware layer.
  - Return `True` on success, `False` on failure.
- **Action:** Remove the old `read_ndef_data` and `write_ndef_data` functions from the controller, as the logic is now integrated into `poll_for_tag` and the new `write_ndef_uri`. Update `__init__.py` exports accordingly.

### 3. Database Module (`backend/modules/database/`)

#### 3.1. `models.py`

- **Reason:** Store URL-based media items and potentially link them to UIDs.
- **Action:** Modify the `MediaItem` model (or equivalent):
  - Add a `url` field: `url = Column(String, unique=True, nullable=True)`. Make it unique so each URL is stored once. Allow it to be null for UID-only entries.
  - Add an index to the `url` column for faster lookups.
  - Consider the relationship between `tag_uid` and `url`. Should `tag_uid` still be the primary key? Or should there be a separate mapping table `TagUidUrlLink(tag_uid, media_item_id)`? A simpler approach for now might be to allow `tag_uid` to be nullable and have either `tag_uid` or `url` identify a media item. If a tag with a UID also has an NDEF URL, the `tag_uid` can be stored alongside the `url` in the `MediaItem` record.
- **Action:** Create a new database migration script (using Alembic or similar if set up) to apply these schema changes.

#### 3.2. `db_manager.py`

- **Reason:** Handle database lookups and insertions based on URLs.
- **Action:** Implement `add_or_get_media_by_url(url, tag_uid=None)`:
  - Query the `MediaItem` table for an entry where `url == url`.
  - If found, return the existing `MediaItem`. If `tag_uid` is provided and not already linked to this item, optionally update the item to include the `tag_uid`.
  - If not found, create a _new_ `MediaItem` record with the provided `url` and `tag_uid` (if provided). Set default values for other fields (like `name`, perhaps derive from URL initially). Add the new item to the session and commit. Return the newly created `MediaItem`.
- **Action:** Review `get_media_for_tag(tag_uid)`: Ensure it correctly retrieves media items associated _only_ with that UID (where `url` might be null).

### 4. Media Module (`backend/modules/media/`)

#### 4.1. `media_manager.py`

- **Reason:** Prepare media for playback using information potentially derived directly from a URL.
- **Action:** Modify `prepare_media(media_info)`:
  - Check if `media_info` (which is likely a `MediaItem` object) has a valid `url` attribute.
  - If yes, use this URL as the source for fetching/streaming via `youtube_handler`.
  - If no URL, fall back to using other attributes (like `file_path` or `name`) as currently implemented.

### 5. API Module (`backend/modules/api/`)

- **Reason:** Expose NDEF writing functionality to the frontend.
- **Action:** Create a new API endpoint (e.g., in `routes.py` or a dedicated `tag_routes.py`).
  - Define a POST route, e.g., `/api/tags/write_ndef`.
  - Expect a JSON body: `{ "uri": "youtube_or_music_url" }`.
  - Implement the route handler:
    - Validate the incoming URI.
    - Instruct the user (via response or WebSocket?) to place a tag on the reader.
    - Enter a loop polling for a tag using `nfc_controller.poll_for_tag()` (maybe just the UID part is needed here, or maybe wait for a tag _without_ NDEF).
    - Once a tag is detected, call `nfc_controller.write_ndef_uri(uri)`.
    - Return a success response (`{ "success": True, "uid": tag_uid }`) or an error response (`{ "success": False, "error": "message" }`) based on the result of the write operation. Handle timeouts if no tag is presented.

### 6. Main Application (`backend/app.py`)

- **Reason:** Integrate the new NDEF reading and database logic into the main playback loop.
- **Action:** Modify `main_loop()`:
  - Change the polling call: `tag_uid, ndef_info = nfc_controller.poll_for_tag()`.
  - Initialize `media_info = None`.
  - **NDEF Handling:**
    - Check if `ndef_info` is not None and contains a valid URI (`ndef_info.get('type') == 'uri'`).
    - Validate if the URI is a YouTube or YouTube Music URL.
    - If valid, call `media_info = db_manager.add_or_get_media_by_url(ndef_info['uri'], tag_uid)`.
  - **UID Handling (if no valid NDEF URL found):**
    - If `media_info` is still `None` and `tag_uid` is not None:
      - Call `media_info = db_manager.get_media_for_tag(tag_uid)`.
  - **Playback:**
    - If `media_info` is now populated (either from NDEF or UID):
      - Proceed with `audio_controller.stop()`, `media_manager.prepare_media(media_info)`, `audio_controller.play(media_path)`.
    - Else (no valid NDEF and unknown UID):
      - Log warning (`logger.warning(f"Unknown tag: UID={tag_uid}, NDEF={ndef_info}")`).
      - Play error sound.

### 7. Testing (`backend/modules/nfc/test_nfc.py`)

- **Reason:** Update tests to reflect new functionality and signatures.
- **Action:**
  - Modify tests that use `poll_for_tag` to expect the new `(uid, ndef_info)` tuple.
  - Update `test_ndef_data` to use the new `write_ndef_uri` function instead of the old `write_ndef_data`.
  - Add specific tests for writing YouTube/Music URLs and verifying them.
  - Add tests for the `NFCTagNotWritableError`.
  - Consider adding integration tests (perhaps in a separate file) that verify the flow through `app.py`, `db_manager`, and `nfc_controller` when an NDEF tag is scanned.

---

## Summary

This implementation involves significant changes primarily within the NFC and Database modules, along with adjustments to the main application loop and API. Using the `ndeflib` library is recommended for simplifying NDEF parsing and creation. Careful testing, especially with different NDEF-compatible tags (like NTAG213, NTAG215, NTAG216), will be crucial.

Please reach out if any part of this plan requires clarification.
