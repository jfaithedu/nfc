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
        
        offset = 0
        
        # Process each record in the NDEF message
        while offset < len(data):
            # Check if we have at least one byte to read the header
            if offset >= len(data):
                break
                
            # Parse header byte
            header = data[offset]
            offset += 1
            
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
            
            header |= 0x10  # Short Record (payload less than 256 bytes)
            header |= NDEF_TNF_WELL_KNOWN  # Well-known type
            
            type_field = NDEF_RTD_URI
            type_length = len(type_field)
            payload_length = len(payload)
            
            record = bytes([header, type_length, payload_length]) + type_field + payload
            records.append(record)
            
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
    message = b''.join(records)
    
    # Ensure it fits into a 16-byte block (or multiple blocks)
    # Pad with zeros if needed
    if len(message) % 16 != 0:
        padding_bytes = 16 - (len(message) % 16)
        message += b'\x00' * padding_bytes
    
    return message
