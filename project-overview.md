## **Project Title**: NFC-Based Toddler-Friendly Music Player

> Winston is 2 years old and loves Bob Marley. This project is to create a durable, toddler-safe music player powered by a Raspberry Pi Zero 2 W, allowing Winston to play specific songs or YouTube playlists by placing NFC-tagged cards on the player.

---

## **Project Overview**

Create a durable, toddler-safe music player powered by a Raspberry Pi Zero 2 W, allowing children to play specific songs or YouTube playlists by tapping NFC-tagged cards. The player will:

- Read NFC tags using an I2C-compatible NFC reader
- Fetch and play audio from YouTube (or local cache)
- Output audio via a connected Bluetooth speaker
- Include a web-based interface (React + TypeScript) for managing media assignments and writing NFC tags
- Be as offline and secure as possible (aside from fetching YouTube content)

---

## **System Architecture**

**Hardware:**

- Raspberry Pi Zero 2 W
- NFC HAT (I2C interface)
- NFC tags (cards, stickers, etc.)
- Bluetooth speaker
- Power supply (consider USB battery bank or mains adapter)
- Optional: GPIO-connected buttons for volume/play/pause

**Software Stack:**

- Backend: Python (for NFC reading, database, and Bluetooth audio control)
- Frontend: React + TypeScript web interface hosted on Pi
- Database: SQLite
- Bluetooth stack: `bluealsa` for streaming audio
- Optional: `youtube-dl` or `yt-dlp` for fetching audio

---

## **Functional Specifications**

### 1. **NFC Interaction**

- Poll for NFC tags using I2C.
- Retrieve tag UID and check for match in SQLite DB.
- Trigger associated audio/media playback on match.

### 2. **Audio Playback**

- Use `yt-dlp` to fetch and stream audio from YouTube or play pre-downloaded audio.
- Send audio to Bluetooth speaker via `bluealsa`.

### 3. **Frontend UI**

- Web-based admin interface:
  - Assign/edit NFC tag to YouTube link or local audio file
  - Write tag metadata
  - Upload local files
  - Test playback
- Local-only (optional login pin for safety)

### 4. **Media Management**

- Option to cache or download audio
- Handle offline mode gracefully
- Maintain small local library for quick access

---

## **Rules & Guidelines**

### **Hardware Guidelines**

- All components must be securely enclosed in a durable, child-safe housing
- NFC reader should be externally accessible with proper shielding
- Avoid small parts; use rounded edges

### **Software Guidelines**

- Fail gracefully: unrecognized tags should not crash the system
- Only pre-approved YouTube links or downloaded media may be played
- NFC tags must be editable only via the admin interface

### **Security Guidelines**

- Local-only network access for admin interface (no cloud exposure)
- Use HTTPS on LAN (with self-signed cert optional)
- All YouTube fetches must be sanitized (block autoplay, ads, etc.)

### **Usability Guidelines**

- Boot directly into service with minimal load time
- No visible command-line interface to the user
- Simple sounds or visual feedback on NFC scan success/failure

### **Parent/Admin Interface Requirements**

- Responsive layout for phone/laptop use
- Tag management view
- Playback test mode
- Backup/restore feature for database and tags
- NFC writer utility

---

## **Future Enhancements**

- Add physical buttons (play/pause/volume)
- Integrate voice feedback or instructions for the child
- NFC tag writer using the web interface
- Offline local music folder scanner
- Daily/weekly usage statistics for parents
