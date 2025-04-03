# NFC Music Player Frontend

This is the admin interface for the NFC-based toddler-friendly music player. It provides a web UI for managing NFC tags, media content, and system settings.

## Development

To start the development server:

```bash
npm install
npm run dev
```

The development server will run on port 5173 by default. API requests are proxied to the backend server at `http://localhost:5000`.

## Building

To build the frontend for production:

```bash
npm run build
```

This will create an optimized build and output the files to `../backend/modules/api/static`. The backend Flask server will then serve these static files.

## Deployment

Since the backend serves the frontend, you just need to build the frontend and restart the backend:

```bash
npm run deploy
```

## Features

- Dashboard with system status
- Tag management
- Media library management
- System settings
- Authentication with PIN protection

## Technology Stack

- React with TypeScript
- Vite for fast development and building
- Tailwind CSS for styling
- Shadcn UI for components
- React Router for navigation
- Axios for API requests
- React Query for data fetching

## Dynamic API URL Handling

The API client automatically handles requests to work with the Raspberry Pi's local IP address by using relative URLs. This ensures that the frontend will work even if the device's IP address changes.