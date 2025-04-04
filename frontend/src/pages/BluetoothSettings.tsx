import { useEffect, useState } from 'react';
import api from '../api/apiClient';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

// Define interfaces for Bluetooth device
interface BluetoothDevice {
    address: string;
    name: string;
    paired: boolean;
    trusted: boolean;
    connected: boolean;
    icon?: string;
    rssi?: number;
    audio_sink: boolean;
}

export default function BluetoothSettings() {
    const [isLoading, setIsLoading] = useState(false);
    const [isScanning, setIsScanning] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [devices, setDevices] = useState<BluetoothDevice[]>([]);
    const [connectedDevice, setConnectedDevice] = useState<BluetoothDevice | null>(null);
    const [actionInProgress, setActionInProgress] = useState<string | null>(null);

    // Function to fetch devices
    const fetchDevices = async () => {
        setError(null);
        setIsLoading(true);

        try {
            const response = await api.system.getBluetoothDevices();

            if (response.data.success) {
                const deviceList = response.data.data.devices;
                const current = response.data.data.current_device;

                setDevices(deviceList);

                if (current) {
                    setConnectedDevice(current);
                } else {
                    setConnectedDevice(null);
                }
            } else {
                setError('Failed to retrieve Bluetooth devices');
            }
        } catch (err) {
            console.error('Error fetching Bluetooth devices:', err);
            setError('Failed to retrieve Bluetooth devices');
        } finally {
            setIsLoading(false);
        }
    };

    // Start scanning for devices
    const startScan = async () => {
        setIsScanning(true);
        setError(null);

        try {
            await fetchDevices();

            // Continue to poll for devices during scan
            const scanInterval = setInterval(async () => {
                await fetchDevices();
            }, 2000);

            // Stop scanning after 30 seconds
            setTimeout(() => {
                clearInterval(scanInterval);
                setIsScanning(false);
            }, 30000);

        } catch (err) {
            console.error('Error scanning for Bluetooth devices:', err);
            setError('Failed to scan for devices');
            setIsScanning(false);
        }
    };

    // Pair with a device (establish trusted relationship without connecting)
    const pairDevice = async (address: string) => {
        setActionInProgress(address);
        setError(null);

        try {
            const response = await api.system.pairBluetooth(address);

            if (response.data.success) {
                await fetchDevices(); // Refresh device list
            } else {
                setError(`Failed to pair with device: ${response.data.error?.message || 'Unknown error'}`);
            }
        } catch (err: unknown) {
            console.error('Error pairing with device:', err);
            const message = err instanceof Error ? err.message : 'Unknown error';
            setError(`Failed to pair with device: ${message}`);
        } finally {
            setActionInProgress(null);
        }
    };

    // Connect to a device (establish active connection)
    const connectDevice = async (address: string, autoPair: boolean = false) => {
        setActionInProgress(address);
        setError(null);

        try {
            const response = await api.system.connectBluetooth(address, autoPair);

            if (response.data.success) {
                await fetchDevices(); // Refresh device list
            } else {
                setError(`Failed to connect to device: ${response.data.error?.message || 'Unknown error'}`);
            }
        } catch (err: unknown) {
            console.error('Error connecting to device:', err);
            const message = err instanceof Error ? err.message : 'Unknown error';
            setError(`Failed to connect to device: ${message}`);
        } finally {
            setActionInProgress(null);
        }
    };

    // Disconnect the current device
    const disconnectDevice = async () => {
        if (!connectedDevice) return;

        setActionInProgress('disconnect');
        setError(null);

        try {
            const response = await api.system.disconnectBluetooth();

            if (response.data.success) {
                setConnectedDevice(null);
                await fetchDevices(); // Refresh device list
            } else {
                setError(`Failed to disconnect device: ${response.data.error?.message || 'Unknown error'}`);
            }
        } catch (err: unknown) {
            console.error('Error disconnecting device:', err);
            const message = err instanceof Error ? err.message : 'Unknown error';
            setError(`Failed to disconnect device: ${message}`);
        } finally {
            setActionInProgress(null);
        }
    };

    // Fetch devices on component mount
    useEffect(() => {
        fetchDevices();
    }, []);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Bluetooth Settings</h1>
                <p className="text-muted-foreground">
                    Manage Bluetooth audio devices for your NFC music player.
                </p>
            </div>

            {error && (
                <div className="bg-destructive/10 p-4 rounded-md border border-destructive">
                    <p className="text-destructive">{error}</p>
                </div>
            )}

            {/* Connected Device Section */}
            <Card>
                <CardHeader>
                    <CardTitle>Connected Device</CardTitle>
                    <CardDescription>
                        Currently connected Bluetooth speaker
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {connectedDevice ? (
                        <div className="space-y-4">
                            <div>
                                <h3 className="font-medium">{connectedDevice.name}</h3>
                                <p className="text-sm text-muted-foreground">{connectedDevice.address}</p>
                            </div>
                            <Button
                                variant="destructive"
                                onClick={disconnectDevice}
                                disabled={actionInProgress === 'disconnect'}
                            >
                                {actionInProgress === 'disconnect' ? 'Disconnecting...' : 'Disconnect'}
                            </Button>
                        </div>
                    ) : (
                        <p className="text-muted-foreground">No device connected</p>
                    )}
                </CardContent>
            </Card>

            {/* Available Devices Section */}
            <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Available Devices</CardTitle>
                        <CardDescription>
                            Bluetooth audio devices in range
                        </CardDescription>
                    </div>
                    <Button
                        onClick={startScan}
                        disabled={isScanning}
                        variant="outline"
                    >
                        {isScanning ? 'Scanning...' : 'Scan'}
                    </Button>
                </CardHeader>
                <CardContent>
                    {isLoading && !devices.length ? (
                        <p className="text-muted-foreground">Loading devices...</p>
                    ) : devices.length > 0 ? (
                        <div className="space-y-4">
                            {devices.map((device) => (
                                <div
                                    key={device.address}
                                    className="border rounded-md p-4 flex flex-col space-y-3"
                                >
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <h3 className="font-medium">{device.name || 'Unknown Device'}</h3>
                                            <p className="text-sm text-muted-foreground">{device.address}</p>
                                            <div className="mt-1 flex space-x-2">
                                                {device.audio_sink && (
                                                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700 ring-1 ring-inset ring-blue-600/20">
                                                        Audio
                                                    </span>
                                                )}
                                                {device.paired && (
                                                    <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-1 text-xs text-green-700 ring-1 ring-inset ring-green-600/20">
                                                        Paired
                                                    </span>
                                                )}
                                                {device.connected && (
                                                    <span className="inline-flex items-center rounded-full bg-purple-50 px-2 py-1 text-xs text-purple-700 ring-1 ring-inset ring-purple-600/20">
                                                        Connected
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        {device.rssi && (
                                            <div className="flex items-center">
                                                <SignalIcon strength={Math.abs(device.rssi)} />
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex flex-wrap gap-2">
                                        {!device.paired && (
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                onClick={() => pairDevice(device.address)}
                                                disabled={actionInProgress === device.address}
                                            >
                                                {actionInProgress === device.address ? 'Pairing...' : 'Pair'}
                                            </Button>
                                        )}

                                        {(device.paired && !device.connected) && (
                                            <Button
                                                size="sm"
                                                onClick={() => connectDevice(device.address)}
                                                disabled={actionInProgress === device.address}
                                            >
                                                {actionInProgress === device.address ? 'Connecting...' : 'Connect'}
                                            </Button>
                                        )}

                                        {(!device.paired && !device.connected) && (
                                            <Button
                                                size="sm"
                                                onClick={() => connectDevice(device.address, true)}
                                                disabled={actionInProgress === device.address}
                                            >
                                                {actionInProgress === device.address ? 'Connecting...' : 'Pair & Connect'}
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-6">
                            <p className="text-muted-foreground">No Bluetooth devices found</p>
                            <p className="text-sm text-muted-foreground mt-1">
                                Make sure your Bluetooth speaker is in pairing mode and click Scan
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}

// Signal strength indicator component
const SignalIcon = ({ strength }: { strength: number }) => {
    // Map RSSI value to signal strength (0-4)
    // Typically, RSSI values range from -30 (very strong) to -100 (very weak)
    let bars = 0;

    if (strength < 50) bars = 4;
    else if (strength < 60) bars = 3;
    else if (strength < 70) bars = 2;
    else if (strength < 80) bars = 1;
    else bars = 0;

    return (
        <div className="flex flex-col items-center">
            <div className="flex items-end h-5 space-x-[2px]">
                {[1, 2, 3, 4].map((level) => (
                    <div
                        key={level}
                        className={`w-1 rounded-sm ${level <= bars
                            ? 'bg-green-600'
                            : 'bg-gray-300'
                            }`}
                        style={{ height: `${level * 3 + 2}px` }}
                    />
                ))}
            </div>
            <span className="text-xs text-muted-foreground mt-1">{-strength} dBm</span>
        </div>
    );
};
