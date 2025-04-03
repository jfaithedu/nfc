import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent 
} from '../components/ui/card';
import { Button } from '../components/ui/button';
import api from '../api/apiClient';
import { getUptime } from '../lib/utils';

interface SystemStatus {
  uptime: number;
  component_status: {
    nfc: boolean;
    api: boolean;
    bluetooth: boolean;
    media: boolean;
  };
  current_bluetooth_device?: {
    name: string;
    address: string;
  };
  volume: number;
}

interface TagCount {
  total: number;
  active: number;
}

interface MediaStats {
  total: number;
  cached: number;
  cache_size_mb: number;
}

export default function Dashboard() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [tagCount, setTagCount] = useState<TagCount | null>(null);
  const [mediaStats, setMediaStats] = useState<MediaStats | null>(null);
  const [lastDetectedTag, setLastDetectedTag] = useState<any>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Get system status
        const systemRes = await api.system.getStatus();
        if (systemRes.data.success) {
          setSystemStatus(systemRes.data.data);
        }
        
        // Get tag count
        const tagsRes = await api.tags.getAll();
        if (tagsRes.data.success) {
          const tags = tagsRes.data.data.tags;
          setTagCount({
            total: tags.length,
            active: tags.filter((tag: any) => tag.media_id).length
          });
        }
        
        // Get media stats
        const mediaRes = await api.media.getAll();
        const cacheRes = await api.media.getCacheStatus();
        if (mediaRes.data.success && cacheRes.data.success) {
          setMediaStats({
            total: mediaRes.data.data.pagination.total,
            cached: cacheRes.data.data.cached_items_count,
            cache_size_mb: cacheRes.data.data.cache_size_mb
          });
        }
        
        // Get last detected tag
        const lastTagRes = await api.tags.getLastDetected();
        if (lastTagRes.data.success && lastTagRes.data.data.last_detected) {
          setLastDetectedTag(lastTagRes.data.data.last_detected);
        }
        
      } catch (err: any) {
        console.error(err);
        setError('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchDashboardData();
    
    // Poll for updates every 5 seconds
    const intervalId = setInterval(fetchDashboardData, 5000);
    
    return () => clearInterval(intervalId);
  }, []);

  if (isLoading && !systemStatus) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <p className="text-destructive">{error}</p>
        <Button onClick={() => window.location.reload()} className="mt-4">
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your NFC music player system.
        </p>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">System Uptime</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemStatus?.uptime ? getUptime(systemStatus.uptime) : 'Unknown'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Volume</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {systemStatus?.volume !== undefined ? `${systemStatus.volume}%` : 'Unknown'}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Tags</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {tagCount ? `${tagCount.active} / ${tagCount.total}` : 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground">Active / Total</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Media Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mediaStats ? mediaStats.total : 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground">
              {mediaStats ? `${mediaStats.cached} cached (${mediaStats.cache_size_mb.toFixed(1)} MB)` : ''}
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>Current status of system components</CardDescription>
          </CardHeader>
          <CardContent>
            {systemStatus?.component_status && (
              <div className="grid gap-2">
                <div className="flex items-center justify-between">
                  <span>NFC Reader</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    systemStatus.component_status.nfc 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.component_status.nfc ? 'Online' : 'Offline'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span>API Server</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    systemStatus.component_status.api 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.component_status.api ? 'Online' : 'Offline'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span>Bluetooth</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    systemStatus.component_status.bluetooth 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.component_status.bluetooth ? 'Online' : 'Offline'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span>Media Service</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    systemStatus.component_status.media 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {systemStatus.component_status.media ? 'Online' : 'Offline'}
                  </span>
                </div>
                
                {systemStatus.current_bluetooth_device && (
                  <div className="mt-4 text-sm">
                    <p className="font-medium">Connected Bluetooth Speaker:</p>
                    <p>{systemStatus.current_bluetooth_device.name}</p>
                    <p className="text-xs text-muted-foreground">{systemStatus.current_bluetooth_device.address}</p>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Last Detected Tag</CardTitle>
            <CardDescription>The most recently scanned NFC tag</CardDescription>
          </CardHeader>
          <CardContent>
            {lastDetectedTag ? (
              <div>
                <p><span className="font-medium">Name:</span> {lastDetectedTag.name || 'Unnamed'}</p>
                <p><span className="font-medium">UID:</span> {lastDetectedTag.uid}</p>
                <p><span className="font-medium">Last Used:</span> {
                  lastDetectedTag.last_used 
                    ? new Date(lastDetectedTag.last_used).toLocaleString() 
                    : 'Never'
                }</p>
                {lastDetectedTag.media_id && (
                  <p className="mt-2">
                    <Link 
                      to={`/media/${lastDetectedTag.media_id}`}
                      className="text-primary hover:underline"
                    >
                      View assigned media
                    </Link>
                  </p>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">No tags detected yet</p>
            )}
          </CardContent>
        </Card>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="col-span-full">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Link to="/tags/new">
              <Button variant="outline" size="sm">Add New Tag</Button>
            </Link>
            <Link to="/media/new">
              <Button variant="outline" size="sm">Add Media</Button>
            </Link>
            <Link to="/system/bluetooth">
              <Button variant="outline" size="sm">Bluetooth Settings</Button>
            </Link>
            <Button 
              variant="outline" 
              size="sm"
              onClick={async () => {
                try {
                  await api.media.stopPlayback();
                  alert('Playback stopped');
                } catch (err) {
                  console.error(err);
                  alert('Failed to stop playback');
                }
              }}
            >
              Stop Playback
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}