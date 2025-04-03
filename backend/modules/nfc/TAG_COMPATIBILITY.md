# NFC Tag Compatibility Guide

## Overview

The NFC module is designed to work with a variety of NFC tag types, but some tags may have specific requirements or limitations. This document provides guidance on tag compatibility and how to resolve common issues.

## Supported Tag Types

The system is designed to work with the following tag types:

1. **NTAG215** (Added special optimizations for this type)
   - 540 bytes total memory (504 bytes user available)
   - 4-byte pages (135 pages total)
   - No authentication required for access
   - Used in many applications including Amiibo, gaming, and general NFC
2. **MIFARE Classic**
   - Most common type of NFC tag
   - Uses authentication with sector keys
   - 1KB or 4KB storage capacity
3. **NTAG / MIFARE Ultralight**
   - No authentication required for reading
   - Simpler communication protocol
   - Limited storage capacity (usually 48 bytes to 888 bytes)
4. **MIFARE DESFire**
   - Advanced security features
   - More complex command set
   - Limited support in the current implementation

## NTAG215 Memory Structure

NTAG215 tags have a specific memory structure:

- **Pages 0-4**: Reserved (manufacturer, serial number, etc.) - Read-only
- **Pages 5-130**: User data (504 bytes) - Read/Write
- **Pages 131-134**: Configuration and lock bytes - Special functionality

When using the API functions, block numbers map to NTAG215 pages as follows:

- Block 0 = Pages 0-3 (manufacturer data, read-only)
- Block 1 = Pages 4-7 (beginning of user memory)
- Block 2 = Pages 8-11 (user memory)
- And so on...

The system will automatically map block numbers to the appropriate NTAG215 pages.

## Common Issues and Solutions

### "Received unexpected command response!" Errors

This error typically occurs when:

1. **Incorrect tag type detection**: The system is trying to use commands for a different tag type.

   - Solution: Try using a different type of tag. NTAG213/215/216 tags often have better compatibility.

2. **Authentication problems**: The tag requires authentication with specific keys.

   - Solution: If using a MIFARE Classic tag, ensure it's not using custom keys. Factory-fresh tags typically use the default keys.

3. **Protected sectors**: Some blocks/sectors on the tag might be protected or locked.

   - Solution: Try reading from or writing to a different block (e.g., block 4-7 are often accessible).

4. **Tag positioning**: Tag is too far from the reader or not properly aligned.

   - Solution: Place the tag directly on the center of the NFC reader and hold it steady.

5. **Hardware limitations**: Some NFC readers might not fully support certain tag operations.
   - Solution: Try a different NFC HAT/reader or use tags that are known to be compatible.

### Write Operation Failures

If write operations fail but reads work:

1. **Write-protected tag**: Some tags are read-only or have write protection enabled.

   - Solution: Verify the tag is not write-protected and can be written to.

2. **Insufficient power**: Writing requires more power than reading.

   - Solution: Ensure the Raspberry Pi is receiving sufficient power.

3. **Block restrictions**: Some blocks (like sector trailers or manufacturer blocks) cannot be written to.
   - Solution: Only write to data blocks, typically blocks 4-7, 8-11, etc., but not blocks 3, 7, 11, etc. (which are sector trailers).

## Write Protection and Lock Bits

The NTAG215 tags have several types of write protection:

1. **Factory write protection**: Manufacturer data in pages 0-4 is permanently read-only.

2. **Static lock bytes**: Pages 2-3 contain lock bits that can permanently protect
   the first 16 pages from being written to.

3. **Dynamic lock bytes**: In page 130, can lock any page in user memory.

4. **Password protection**: Pages 133-134 can enable password authentication for writing.

If you encounter write errors only, but reads work fine, your tag may have some form of
write protection enabled. This is detected automatically and reported as "Tag appears to
be read-only or write-protected".

## Recommended NFC Tags

For best compatibility:

1. **NTAG215**: 504 bytes user memory, now specially supported by this implementation.
2. **NTAG213/216**: Similar to NTAG215 with 144 bytes/888 bytes of user memory respectively.
3. **MIFARE Ultralight**: Similar to NTAG, with simple access.
4. **MIFARE Classic 1K**: Widely supported, but requires proper authentication.

## Testing Tag Compatibility

You can test if a tag is compatible with your system by:

1. Running the hardware detection test to verify reader functionality:

   ```
   python3 test_nfc.py -t hardware
   ```

2. Testing basic tag detection:

   ```
   python3 test_nfc.py -t detect
   ```

3. If the tag is detected but read/write fails, try using the tag with NFC tools on a smartphone to determine its type and capabilities.

## Advanced Troubleshooting

For persistent issues:

1. Enable verbose debugging:

   ```
   python3 test_nfc.py -v --debug
   ```

2. Try direct block access using lower-level tools like `nfc-mfclassic` if available.

3. Check the tag with a smartphone NFC app to verify it's functioning and determine its precise type.

4. For specialized tags or custom keys, you may need to modify the `hardware_interface.py` file to add support for your specific tag configuration.
