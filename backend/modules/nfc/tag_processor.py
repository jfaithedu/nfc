"""
tag_processor.py - Functions for processing NFC tag data.
"""

import logging
import struct
from .exceptions import NFCError

# Create logger
logger = logging.getLogger(__name__)

def format_uid(raw_uid):
    """
    Format raw UID bytes to a standardized string format.

    Args:
        raw_uid (bytes): Raw UID from NFC reader

    Returns:
        str: Formatted UID string (hex format, uppercase)
    """
    if not raw_uid:
        return None
        
    try:
        # Convert bytes to uppercase hex string with no spaces
        uid_hex = raw_uid.hex().upper()
        
        # Format with colons for readability (e.g., "AA:BB:CC:DD")
        uid_formatted = ':'.join(uid_hex[i:i+2] for i in range(0, len(uid_hex), 2))
        
        return uid_formatted
    except Exception as e:
        logger.error(f"Error formatting UID: {str(e)}")
        return None

# NDEF Record Type Definitions
NDEF_TNF_EMPTY = 0x00
NDEF_TNF_WELL_KNOWN = 0x01
NDEF_TNF_MIME_MEDIA = 0x02
NDEF_TNF_URI = 0x03
NDEF_TNF_EXTERNAL = 0x04
NDEF_TNF_UNKNOWN = 0x05
NDEF_TNF_UNCHANGED = 0x06

# Well Known Type definitions
NDEF_RTD_TEXT = b'T'
NDEF_RTD_URI = b'U'

# URI Record Type prefixes
URI_PREFIXES = [
    '',                            # 0x00
    'http://www.',                # 0x01
    'https://www.',               # 0x02
    'http://',                    # 0x03
    'https://',                   # 0x04
    'tel:',                       # 0x05
    'mailto:',                    # 0x06
    'ftp://anonymous:anonymous@', # 0x07
    'ftp://ftp.',                 # 0x08
    'ftps://',                    # 0x09
    'sftp://',                    # 0x0A
    'smb://',                     # 0x0B
    'nfs://',                     # 0x0C
    'ftp://',                     # 0x0D
    'dav://',                     # 0x0E
    'news:',                      # 0x0F
    'telnet://',                  # 0x10
    'imap:',                      # 0x11
    'rtsp://',                    # 0x12
    'urn:',                       # 0x13
    'pop:',                       # 0x14
    'sip:',                       # 0x15
    'sips:',                      # 0x16
    'tftp:',                      # 0x17
    'btspp://',                   # 0x18
    'btl2cap://',                 # 0x19
    'btgoep://',                  # 0x1A
    'tcpobex://',                 # 0x1B
    'irdaobex://',                # 0x1C
    'file://',                    # 0x1D
    'urn:epc:id:',                # 0x1E
    'urn:epc:tag:',               # 0x1F
    'urn:epc:pat:',               # 0x20
    'urn:epc:raw:',               # 0x21
    'urn:epc:',                   # 0x22
    'urn:nfc:',                   # 0x23
]

def parse_ndef_data(data):
    """
    Parse NDEF formatted data from tag.

    Args:
        data (bytes): Raw data read from tag

    Returns:
        dict: Parsed NDEF message and records
    """
    if not data or len(data) < 2:
        return None
    
    try:
        result = {
            'message_type': 'NDEF',
            'records': []
        }
        
        # Special handling for NTAG215 tags
        # NTAG215 tags use Type 2 Tag format with a specific TLV structure:
        # - Byte 0: TLV Tag (0x03 for NDEF)
        # - Byte 1: TLV Length
        # - Bytes 2+: NDEF Message

        # Check for Type 2 Tag structure (common for NTAG215)
        if data[0] == 0x03:  # Type 2 Tag, NDEF Message TLV
            # Parse TLV structure
            tlv_type = data[0]
            
            # Check for 3-byte length format
            if len(data) > 1 and data[1] == 0xFF and len(data) >= 4:
                # 3-byte length format
                tlv_length = int.from_bytes(data[2:4], byteorder='big')
                start_offset = 4  # After the 3-byte length field
                logger.debug(f"Found TLV with 3-byte length format: {tlv_length} bytes")
            else:
                # Standard 1-byte length format
                tlv_length = data[1]
                start_offset = 2  # After the 1-byte length field
            
            # If we find a valid NDEF TLV block
            if tlv_type == 0x03 and tlv_length > 0 and len(data) >= tlv_length + start_offset:
                # Extract the NDEF message from the TLV
                ndef_data = data[start_offset:start_offset+tlv_length]
                
                # Now process the NDEF message
                data = ndef_data
                logger.debug(f"Extracted {len(ndef_data)} bytes of NDEF data from TLV")
            
        # Check for NTAG215 common format where the first byte is the NDEF message length
        elif len(data) > 2 and data[0] > 0 and data[0] < len(data) and data[1] in [0x01, 0x03, 0xD1]:
            # This might be an NTAG215 with the message length as the first byte
            message_length = data[0]
            if message_length < len(data):
                # Extract the actual NDEF message
                data = data[1:1+message_length]
        
        offset = 0
        
        # Process each record in the NDEF message
        while offset < len(data):
            # Check if we have at least one byte to read the header
            if offset >= len(data):
                break
                
            # Parse header byte
            header = data[offset]
            offset += 1
            
            # Check if this is terminative TLV (0xFE)
            if header == 0xFE:
                # End of NDEF message, finished processing
                break
                
            # Check if this is null TLV (0x00), just skip it and continue
            if header == 0x00:
                continue
                
            # If not a standard NDEF record header, we might be dealing with a non-standard format
            if header not in [0x03, 0xD1, 0x91, 0x51, 0x11, 0x01]:  # Common NDEF header values
                # Try to reset and scan for a valid NDEF header
                found_header = False
                for i in range(offset, min(offset + 10, len(data))):
                    if data[i] in [0x03, 0xD1, 0x91, 0x51, 0x11, 0x01]:
                        offset = i
                        header = data[offset]
                        offset += 1
                        found_header = True
                        break
                
                if not found_header:
                    # No valid header found, stop processing
                    break
            
            mb = (header & 0x80) != 0  # Message Begin
            me = (header & 0x40) != 0  # Message End
            cf = (header & 0x20) != 0  # Chunk Flag
            sr = (header & 0x10) != 0  # Short Record
            il = (header & 0x08) != 0  # ID Length present
            tnf = header & 0x07        # Type Name Format
            
            # Check if we have enough data to read type length
            if offset >= len(data):
                break
                
            type_length = data[offset]
            offset += 1
            
            # Payload length - short record (1 byte) or normal (4 bytes)
            if sr:
                if offset >= len(data):
                    break
                payload_length = data[offset]
                offset += 1
            else:
                if offset + 3 >= len(data):
                    break
                payload_length = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
            
            # ID Length and ID (if present)
            id_length = 0
            id_value = b''
            if il:
                if offset >= len(data):
                    break
                id_length = data[offset]
                offset += 1
                
                if id_length > 0:
                    if offset + id_length > len(data):
                        break
                    id_value = data[offset:offset+id_length]
                    offset += id_length
            
            # Type
            type_value = b''
            if type_length > 0:
                if offset + type_length > len(data):
                    break
                type_value = data[offset:offset+type_length]
                offset += type_length
            
            # Payload
            payload = b''
            if payload_length > 0:
                if offset + payload_length > len(data):
                    break
                payload = data[offset:offset+payload_length]
                offset += payload_length
            
            # Create record dict
            record = {
                'type_name_format': tnf,
                'type': type_value,
                'id': id_value,
                'payload': payload
            }
            
            # Process well-known types
            if tnf == NDEF_TNF_WELL_KNOWN:
                if type_value == NDEF_RTD_TEXT:
                    # Text record
                    status_byte = payload[0]
                    language_code_length = status_byte & 0x3F
                    encoding = 'utf-16' if (status_byte & 0x80) else 'utf-8'
                    
                    language_code = payload[1:1+language_code_length].decode('ascii')
                    text = payload[1+language_code_length:].decode(encoding)
                    
                    record['decoded'] = {
                        'type': 'text',
                        'language': language_code,
                        'encoding': encoding,
                        'text': text
                    }
                    
                elif type_value == NDEF_RTD_URI:
                    # URI record
                    prefix_index = payload[0]
                    prefix = URI_PREFIXES[prefix_index] if prefix_index < len(URI_PREFIXES) else ''
                    uri = prefix + payload[1:].decode('utf-8')
                    
                    record['decoded'] = {
                        'type': 'uri',
                        'uri': uri
                    }
            
            result['records'].append(record)
            
            # If this was the end of the message, stop parsing
            if me:
                break
        
        return result
        
    except Exception as e:
        logger.error(f"Error parsing NDEF data: {str(e)}")
        return None

def create_ndef_data(url=None, text=None):
    """
    Create NDEF formatted data for writing to tag.

    Args:
        url (str, optional): URL to encode
        text (str, optional): Text to encode

    Returns:
        bytes: NDEF formatted data ready for writing
    """
    if not url and not text:
        raise ValueError("Either url or text must be provided")
    
    records = []
    
    if url:
        # Create URI record
        try:
            # Find the best matching prefix
            prefix_index = 0
            for i, prefix in enumerate(URI_PREFIXES):
                if prefix and url.startswith(prefix):
                    prefix_index = i
                    url = url[len(prefix):]  # Remove prefix from URL
                    break
            
            # Create payload with prefix index + URI
            payload = bytes([prefix_index]) + url.encode('utf-8')
            
            # Create NDEF record
            header = 0
            if len(records) == 0:
                header |= 0x80  # Message Begin
            if not text:  # If this is the only/last record
                header |= 0x40  # Message End
            
            # Short Record flag for payloads < 256 bytes
            if len(payload) < 256:
                header |= 0x10  # Short Record
            
            header |= NDEF_TNF_WELL_KNOWN  # Well-known type
            
            type_field = NDEF_RTD_URI
            type_length = len(type_field)
            payload_length = len(payload)
            
            # Create record header
            if header & 0x10:  # Short Record
                record = bytes([header, type_length, payload_length])
            else:
                # Long record format with 4-byte length
                record = bytes([header, type_length]) + payload_length.to_bytes(4, byteorder='big')
            
            # Add type and payload
            record += type_field + payload
            records.append(record)
            
            logger.debug(f"Created URI record with {len(payload)} bytes of payload data")
            
        except Exception as e:
            logger.error(f"Error creating URI record: {str(e)}")
            raise NFCError(f"Failed to create URI record: {str(e)}")
    
    if text:
        # Create Text record
        try:
            # Use UTF-8 encoding
            encoding_flag = 0x00  # UTF-8
            language_code = b'en'  # English
            
            # Create payload with status byte + language code + text
            status_byte = encoding_flag | (len(language_code) & 0x3F)
            payload = bytes([status_byte]) + language_code + text.encode('utf-8')
            
            # Create NDEF record
            header = 0
            if len(records) == 0:
                header |= 0x80  # Message Begin
            header |= 0x40  # Message End (always the last record)
            header |= 0x10  # Short Record (payload less than 256 bytes)
            header |= NDEF_TNF_WELL_KNOWN  # Well-known type
            
            type_field = NDEF_RTD_TEXT
            type_length = len(type_field)
            payload_length = len(payload)
            
            record = bytes([header, type_length, payload_length]) + type_field + payload
            records.append(record)
            
        except Exception as e:
            logger.error(f"Error creating Text record: {str(e)}")
            raise NFCError(f"Failed to create Text record: {str(e)}")
    
    # Combine all records into a single message
    ndef_message = b''.join(records)
    
    # For NTAG215, we need to create proper Type 2 Tag structure with TLV format
    # This is a simple Type 2 Tag TLV structure used by NTAG215
    tlv_type = bytes([0x03])  # NDEF Message TLV
    
    # Handle TLV length properly - for lengths > 254, we need to use a 3-byte format
    message_length = len(ndef_message)
    
    if message_length < 255:
        # Standard 1-byte length format
        tlv_length = bytes([message_length])
        tlv_data = tlv_type + tlv_length + ndef_message
    else:
        # 3-byte length format for lengths >= 255
        tlv_length = bytes([0xFF]) + message_length.to_bytes(2, byteorder='big')
        tlv_data = tlv_type + tlv_length + ndef_message
        logger.debug(f"Using 3-byte TLV length format for message length {message_length}")
    
    # Add a terminator TLV if needed
    if len(tlv_data) < 16:  # If there's room in the first block
        tlv_data += bytes([0xFE])  # Terminator TLV
    
    # Ensure it fits into a 16-byte block (or multiple blocks)
    # Pad with zeros if needed
    if len(tlv_data) % 16 != 0:
        padding_bytes = 16 - (len(tlv_data) % 16)
        tlv_data += b'\x00' * padding_bytes
    
    return tlv_data
