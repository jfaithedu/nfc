import axios from 'axios';
import { getApiUrl } from '../lib/utils';

// Define interfaces for API data structures
interface TagData {
  name: string;
  description?: string;
  media_id?: string | null;
  // Add other potential tag properties if known
}

interface YouTubeData {
  url: string;
  // Add other potential YouTube data properties if known
}

interface SettingsData {
  // Define properties based on what settings can be updated
  // Example:
  pin_enabled?: boolean;
  auto_play_delay?: number;
  // ... other settings based on actual API
}

interface NfcWriteStartData {
  media_id: string;
  // Add other potential properties if needed
}

interface NfcWriteTagData {
  // Define the structure of data written to a tag
  // Example:
  content: string; // Adjust based on actual data structure
}

interface NdefData {
  // Define the structure for NDEF data
  // Example:
  records: Array<{ type: string; payload: string }>; // Adjust based on actual data structure
}


// Create axios instance with base URL that will work with the dynamic IP
const apiClient = axios.create({
  baseURL: getApiUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the token for authenticated routes
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// API functions
export const api = {
  // Auth endpoints
  auth: {
    login: (pin: string) => apiClient.post('/api/auth/login', { pin }),
  },

  // Tags endpoints
  tags: {
    getAll: () => apiClient.get('/api/tags'),
    getById: (uid: string) => apiClient.get(`/api/tags/${uid}`),
    create: (data: TagData) => apiClient.post('/api/tags', data),
    update: (uid: string, data: Partial<TagData>) => apiClient.put(`/api/tags/${uid}`, data),
    delete: (uid: string) => apiClient.delete(`/api/tags/${uid}`),
    associate: (uid: string, mediaId: string) =>
      apiClient.post(`/api/tags/${uid}/associate`, { media_id: mediaId }),
    getLastDetected: () => apiClient.get('/api/tags/last-detected'),
    getHistory: (limit = 10, offset = 0) =>
      apiClient.get(`/api/tags/history?limit=${limit}&offset=${offset}`),
  },

  // Media endpoints
  media: {
    getAll: (limit = 20, offset = 0) =>
      apiClient.get(`/api/media?limit=${limit}&offset=${offset}`),
    getById: (id: string) => apiClient.get(`/api/media/${id}`),
    addYouTube: (data: YouTubeData) => apiClient.post('/api/media/youtube', data),
    upload: (formData: FormData) =>
      apiClient.post('/api/media/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    delete: (id: string) => apiClient.delete(`/api/media/${id}`),
    testPlayback: (id: string) => apiClient.post(`/api/media/${id}/test`),
    stopPlayback: () => apiClient.post('/api/media/playback/stop'),
    download: (id: string) => apiClient.get(`/api/media/${id}/download`),
    getCacheStatus: () => apiClient.get('/api/media/cache/status'),
    cleanCache: (force = false) => apiClient.post('/api/media/cache/clean', { force }),
  },

  // System endpoints
  system: {
    getStatus: () => apiClient.get('/api/system/status'),
    getBluetoothDevices: () => apiClient.get('/api/system/bluetooth/devices'),
    pairBluetooth: (address: string) =>
      apiClient.post('/api/system/bluetooth/pair', { address }),
    connectBluetooth: (address: string, autoPair: boolean = true) =>
      apiClient.post('/api/system/bluetooth/connect', { address, auto_pair: autoPair }),
    disconnectBluetooth: () => apiClient.post('/api/system/bluetooth/disconnect'),
    setVolume: (volume: number) => apiClient.post('/api/system/volume', { volume }),
    getSettings: () => apiClient.get('/api/system/settings'),
    updateSettings: (settings: SettingsData) => apiClient.put('/api/system/settings', settings),
    changePin: (currentPin: string, newPin: string) =>
      apiClient.post('/api/system/change_pin', { current_pin: currentPin, new_pin: newPin }),
    backup: () => apiClient.post('/api/system/backup', {}, { responseType: 'blob' }),
    restore: (backupFile: File, pin: string) => {
      const formData = new FormData();
      formData.append('backup_file', backupFile);
      formData.append('pin', pin);
      return apiClient.post('/api/system/restore', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    },
    restart: (pin: string) => apiClient.post('/api/system/restart', { pin }),
  },

  // NFC writer endpoints
  nfc: {
    startWriteMode: (data: NfcWriteStartData) => apiClient.post('/api/nfc/write/start', data),
    stopWriteMode: () => apiClient.post('/api/nfc/write/stop'),
    getWriteStatus: () => apiClient.get('/api/nfc/write/status'),
    writeToTag: (uid: string, data: NfcWriteTagData) => apiClient.post(`/api/nfc/write/${uid}`, { data }),
    readRaw: () => apiClient.get('/api/nfc/read'),
    readNdef: () => apiClient.get('/api/nfc/ndef/read'),
    writeNdef: (data: NdefData) => apiClient.post('/api/nfc/ndef/write', data),
  },

  // Health check
  health: () => apiClient.get('/api/health'),
};

export default api;
