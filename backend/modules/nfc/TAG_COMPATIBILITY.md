# NFC Tag Compatibility Guide

## Overview

The NFC module is designed to work with a variety of NFC tag types, but some tags may have specific requirements or limitations. This document provides guidance on tag compatibility and how to resolve common issues.

## Supported Tag Types

The system is designed to work with the following tag types:

1. **MIFARE Classic**
   - Most common type of NFC tag
   - Uses authentication with sector keys
   - 1KB or 4KB storage capacity
2. **NTAG / MIFARE Ultralight**
   - No authentication required for reading
   - Simpler communication protocol
   - Limited storage capacity (usually 48 bytes to 888 bytes)
3. **MIFARE DESFire**
   - Advanced security features
   - More complex command set
   - Limited support in the current implementation

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

## Recommended NFC Tags

For best compatibility:

1. **NTAG213/215/216**: Good general-purpose tags without authentication requirements.
2. **MIFARE Ultralight**: Similar to NTAG, with simple access.
3. **MIFARE Classic 1K**: Widely supported, but requires proper authentication.

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
