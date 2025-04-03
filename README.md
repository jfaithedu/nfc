# NFC-Based Toddler-Friendly Music Player

A Raspberry Pi-powered music player that uses NFC cards to play specific songs or YouTube playlists, designed for toddlers.

## Overview

This project creates a durable, toddler-safe music player using a Raspberry Pi Zero 2 W that allows children to play specific songs or YouTube playlists by placing NFC-tagged cards on the reader. The system includes:

- NFC tag reading via an I2C-compatible NFC reader
- Media fetching and playing from YouTube (or local cache)
- Audio output via a connected Bluetooth speaker
- A web-based admin interface for managing media and NFC tags

## Repository Structure

- `/backend`: Python backend for NFC reading, database, and audio control
- `/frontend`: React + TypeScript web interface

## Getting Started

### Prerequisites

- Raspberry Pi Zero 2 W (or similar)
- NFC HAT with I2C interface
- NFC tags (cards, stickers, etc.)
- Bluetooth speaker
- Power supply

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nfc-music-player.git
   cd nfc-music-player
   ```

2. Set up the Python environment:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Install frontend dependencies:
   ```bash
   cd ../frontend
   npm install
   ```

4. Build the frontend:
   ```bash
   npm run build
   ```

## Running the Application

### Standalone Frontend (Development)

```bash
cd frontend
npm run dev
```

### Full System

From the project root:

```bash
# Build frontend and start backend
npm run start
```

## Accessing the Admin Interface

Once the application is running, access the admin interface:

- Local development: http://localhost:5173
- Production/Raspberry Pi: http://[raspberry-pi-ip]:5000

The default PIN is `1234`.

## Features

- **NFC Interaction**: Scan NFC cards to play associated media
- **Audio Playback**: Stream from YouTube or play pre-downloaded audio
- **Admin Interface**: Web-based interface for:
  - Assigning NFC tags to media
  - Writing tag metadata
  - Uploading local files
  - Testing playback
  - Managing system settings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.