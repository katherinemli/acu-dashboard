"""
metadata.py - Field definitions for Eureka Dashboard forms

Edit this file to change labels, help text, placeholders, validation, etc.
No rebuild required - just restart the eureka service:
    sudo systemctl restart eureka
"""

SECTION_METADATA = {
    'system': {
        'title': 'System Configuration',
        'fields': [
            {
                'key': 'acuName',
                'label': 'Name',
                'type': 'text',
                'placeholder': 'ex: Montreal1',
                'help': 'Unique identifier for this ACU (letters, numbers, hyphens only, max 63 chars)',
                'pattern': '^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]$',
                'maxlength': 63
            },
            {
                'key': 'modemType',
                'label': 'Modem Type',
                'type': 'select',
                'options': ['Comtech', 'None'],
                'placeholder': 'Comtech',
                'help': 'Satellite modem manufacturer/model'
            },
            {
                'key': 'modemIp',
                'label': 'Modem IP Address',
                'type': 'text',
                'placeholder': 'ex: 192.168.100.99',
                'help': 'IP address of the satellite modem'
            },
            {
                'key': 'modemPort',
                'label': 'Modem Port',
                'type': 'number',
                'placeholder': 'ex: 5005',
                'min': 1024,
                'max': 65535,
                'help': 'Communication port for modem connection'
            },
            {
                'key': 'acuDesc',
                'label': 'Description',
                'type': 'text',
                'placeholder': 'ex: 1.2m Ku-Band',
                'help': 'Brief description of this antenna system'
            },
            {
                'key': 'acuLocation',
                'label': 'Location',
                'type': 'text',
                'placeholder': 'ex: Rooftop Building A',
                'help': 'Physical installation location (e.g. rooftop, cabinet)'
            },
            {
                'key': 'acuTz',
                'label': 'Timezone',
                'type': 'select',
                'options': [
                    'utc-12', 'utc-11', 'utc-10', 'utc-9:30', 'utc-9',
                    'utc-8', 'utc-7', 'utc-6', 'utc-5', 'utc-4:30',
                    'utc-4', 'utc-3:30', 'utc-3', 'utc-2', 'utc-1',
                    'utc+0',
                    'utc+1', 'utc+2', 'utc+3', 'utc+3:30', 'utc+4',
                    'utc+4:30', 'utc+5', 'utc+5:30', 'utc+5:45', 'utc+6',
                    'utc+6:30', 'utc+7', 'utc+8', 'utc+8:45', 'utc+9',
                    'utc+9:30', 'utc+10', 'utc+10:30', 'utc+11', 'utc+12',
                    'utc+12:45', 'utc+13', 'utc+14'
                ],
                'placeholder': 'utc-5',
                'help': 'UTC offset for this site',
            },
        ]
    },
    'network': {
        'title': 'Network Configuration',
        'fields': [
            {
                'key': 'acuIpPriv',
                'label': 'Internal IP Address',
                'type': 'text',
                'placeholder': 'ex: 192.168.100.102',
                'help': 'Internal IP address (read-only)',
                'readonly': True
            },
            {
                'key': 'acuMaskPriv',
                'label': 'Internal Subnet Mask',
                'type': 'text',
                'placeholder': 'ex: 255.255.255.248',
                'help': 'Internal network subnet mask (read-only)',
                'readonly': True
            },
            {
                'key': 'acuIp',
                'label': 'MGMT IP Address',
                'type': 'text',
                'placeholder': 'ex: 192.168.222.223',
                'help': 'Static IP address assigned to the ACU'
            },
            {
                'key': 'acuMask',
                'label': 'MGMT Subnet Mask',
                'type': 'text',
                'placeholder': 'ex: 255.255.255.0',
                'help': 'Network subnet mask'
            },
            {
                'key': 'acuGateway',
                'label': 'MGMT Gateway',
                'type': 'text',
                'placeholder': 'ex: 192.168.100.1',
                'help': 'Default gateway for network routing'
            },
            {
                'key': 'acuDns',
                'label': 'DNS Server',
                'type': 'text',
                'placeholder': 'ex: 8.8.8.8',
                'help': 'DNS nameserver applied via nmcli on save (default: 8.8.8.8)'
            }
        ]
    },
    'sensors': {
        'title': 'Advanced Configuration',
        'fields': [
            {
                'key': 'gyroRange',
                'label': 'Gyro Range',
                'type': 'number',
                'placeholder': 'ex: 20000',
                'min': 250,
                'max': 50000,
                'help': 'Gyroscope measurement range in deg/s',
                'hidden': True
            },
            {
                'key': 'accRange',
                'label': 'Accelerometer Range',
                'type': 'number',
                'placeholder': 'ex: 2',
                'min': 1,
                'max': 16,
                'help': 'Accelerometer range in +/-g units (default=2)'
            }
        ]
    },
    'advanced': {
        'title': 'Pointing Configuration',
        'fields': [
            {
                'key': 'azSearchWindowDeg',
                'label': 'Az Search Window',
                'type': 'number',
                'placeholder': 'ex: 20',
                'min': 1,
                'max': 90,
                'step': '1',
                'help': 'Azimuth scan window in degrees (total, centered on TLE az)'
            },
            {
                'key': 'elSearchWindowDeg',
                'label': 'El Search Window',
                'type': 'number',
                'placeholder': 'ex: 6',
                'min': 1,
                'max': 45,
                'step': '1',
                'help': 'Elevation scan window in degrees (total, centered on TLE el)'
            },
            {
                'key': 'searchAngleStepDeg',
                'label': 'Search Step',
                'type': 'number',
                'placeholder': 'ex: 1',
                'min': 0.1,
                'max': 5,
                'step': '0.1',
                'help': 'Step size in degrees between scan positions'
            },
            {
                'key': 'peakingAngleStepDeg',
                'label': 'Peaking Step',
                'type': 'number',
                'placeholder': 'ex: 0.25',
                'min': 0.05,
                'max': 2,
                'step': '0.05',
                'help': 'Step size in degrees used during signal peaking'
            },
            {
                'key': 'peakingPeriod',
                'label': 'Peaking Period',
                'type': 'number',
                'placeholder': 'ex: 15',
                'min': 5,
                'max': 300,
                'step': '1',
                'help': 'Seconds between peaking cycles while tracking'
            },
            {
                'key': 'peakingStepCoefficient',
                'label': 'Peaking Step Coefficient',
                'type': 'number',
                'placeholder': 'ex: 4',
                'min': 1,
                'max': 20,
                'step': '1',
                'help': 'Divisor applied to peaking step during fine peaking (higher = finer steps)'
            },
            {
                'key': 'rfThresholdLevel',
                'label': 'RF Detection Threshold',
                'type': 'number',
                'placeholder': 'ex: 30',
                'min': 1,
                'max': 200,
                'step': '1',
                'help': 'RF level delta above noise floor (in 0.1 dBm units) required to flag satellite candidate'
            },
            {
                'key': 'carrierLockTimeout',
                'label': 'Lock Wait Timeout',
                'type': 'number',
                'placeholder': 'ex: 5',
                'min': 1,
                'max': 60,
                'step': '1',
                'help': 'Seconds to wait for modem carrier lock after a candidate is found'
            },
            {
                'key': 'pointingRestartTimer',
                'label': 'Pointing Restart Timer',
                'type': 'number',
                'placeholder': 'ex: 30',
                'min': 10,
                'max': 300,
                'step': '1',
                'help': 'Seconds before restarting the pointing cycle if lock is not achieved'
            },
        ]
    },
    'esa': {
        'title': 'ESA Configuration',
        'fields': [
            {
                'key': 'esaTxIp',
                'label': 'ESA TX IP Address',
                'type': 'text',
                'placeholder': 'ex: 192.168.100.100',
                'help': 'ESA TX controller IP address (default=192.168.100.100)'
            },
            {
                'key': 'esaTxPort',
                'label': 'ESA TX Port',
                'type': 'number',
                'placeholder': 'ex: 5005',
                'min': 1024,
                'max': 65535,
                'help': 'Port for outgoing ESA data (default=5005)'
            },
            {
                'key': 'esaRxIp',
                'label': 'ESA RX IP Address',
                'type': 'text',
                'placeholder': 'ex: 192.168.100.101',
                'help': 'ESA RX controller IP address (default=192.168.100.101)'
            },
            {
                'key': 'esaRxPort',
                'label': 'ESA RX Port',
                'type': 'number',
                'placeholder': 'ex: 5005',
                'min': 1024,
                'max': 65535,
                'help': 'Port for incoming ESA data (default=5005)'
            }
        ]
    },
    'location': {
        'title': 'Location Configuration',
        'fields': [
            {
                'key': 'SiteLocOverride',
                'label': 'GPS Mode',
                'type': 'button-group',
                'options': [
                    {'value': '0', 'label': 'GPS'},
                    {'value': '1', 'label': 'Manual'}
                ],
                'placeholder': '0',
                'help': 'GPS = use GPS receiver, Manual = enter coordinates below'
            },
            {
                'key': 'latDeg',
                'label': 'Lat Degrees',
                'type': 'number',
                'placeholder': 'ex: 45',
                'min': 0,
                'max': 89,
                'help': 'Latitude degrees'
            },
            {
                'key': 'latMin',
                'label': 'Lat Minutes',
                'type': 'number',
                'placeholder': 'ex: 30',
                'min': 0,
                'max': 59,
                'help': 'Latitude minutes'
            },
            {
                'key': 'latSec',
                'label': 'Lat Seconds',
                'type': 'number',
                'placeholder': 'ex: 0.0',
                'min': 0,
                'max': 59.9999,
                'step': 0.0001,
                'help': 'Latitude seconds (decimal)'
            },
            {
                'key': 'latNS',
                'label': 'N/S',
                'type': 'select',
                'options': ['North', 'South'],
                'placeholder': 'North',
                'help': 'North or South hemisphere'
            },
            {
                'key': 'lonDeg',
                'label': 'Lon Degrees',
                'type': 'number',
                'placeholder': 'ex: 73',
                'min': 0,
                'max': 179,
                'help': 'Longitude degrees'
            },
            {
                'key': 'lonMin',
                'label': 'Lon Minutes',
                'type': 'number',
                'placeholder': 'ex: 34',
                'min': 0,
                'max': 59,
                'help': 'Longitude minutes'
            },
            {
                'key': 'lonSec',
                'label': 'Lon Seconds',
                'type': 'number',
                'placeholder': 'ex: 0.0',
                'min': 0,
                'max': 59.9999,
                'step': 0.0001,
                'help': 'Longitude seconds (decimal)'
            },
            {
                'key': 'lonEW',
                'label': 'E/W',
                'type': 'select',
                'options': ['East', 'West'],
                'placeholder': 'West',
                'help': 'East or West hemisphere'
            },
            {
                'key': 'altitude',
                'label': 'Altitude',
                'type': 'number',
                'placeholder': 'ex: 50',
                'min': -500,
                'max': 10000,
                'help': 'Site altitude above sea level in meters'
            }
        ]
    },
}

SATELLITE_FIELDS = [
    {
        'key': 'satName',
        'label': 'Name',
        'type': 'text',
        'placeholder': 'ex: ST-2',
        'help': 'Display name of the target satellite',
        'required': True
    },
    {
        'key': 'satNoradId',
        'label': 'NORAD ID',
        'type': 'number',
        'placeholder': 'ex: 37606',
        'min': 1,
        'max': 99999,
        'help': 'NORAD catalog number for satellite tracking'
    },
    {
        'key': 'satOperator',
        'label': 'Operator',
        'type': 'text',
        'placeholder': 'ex: SingTel',
        'help': 'Satellite operator/owner'
    },
    {
        'key': 'satLong',
        'label': 'Longitude',
        'type': 'number',
        'placeholder': 'ex: 88',
        'min': 0,
        'max': 180,
        'step': 0.1,
        'help': 'Orbital longitude in degrees'
    },
    {
        'key': 'satLongEW',
        'label': 'Long E/W',
        'type': 'select',
        'options': ['E', 'W'],
        'placeholder': 'E',
        'help': 'East or West hemisphere'
    },
    {
        'key': 'satSkewOffset',
        'label': 'Skew Offset',
        'type': 'number',
        'placeholder': 'ex: -2',
        'min': -90,
        'max': 90,
        'step': 0.1,
        'help': 'Polarization skew offset in degrees'
    },
    {
        'key': 'satRxPol',
        'label': 'RX Polarization',
        'type': 'select',
        'options': ['V', 'H', 'LHCP', 'RHCP'],
        'placeholder': 'V',
        'help': 'Receive polarization'
    },
    {
        'key': 'satTxPol',
        'label': 'TX Polarization',
        'type': 'select',
        'options': ['V', 'H', 'LHCP', 'RHCP'],
        'placeholder': 'H',
        'help': 'Transmit polarization'
    },
    {
        'key': 'satLoFreqkHz',
        'label': 'LO Frequency',
        'type': 'number',
        'placeholder': 'ex: 10360000',
        'min': 0,
        'max': 99999999,
        'help': 'Local oscillator frequency in kHz'
    },
    {
        'key': 'satBandMhz',
        'label': 'Band',
        'type': 'number',
        'placeholder': 'ex: 11036',
        'min': 0,
        'max': 99999,
        'help': 'Satellite band frequency in MHz'
    },
    {
        'key': 'satBandwidthkHz',
        'label': 'Bandwidth',
        'type': 'number',
        'placeholder': 'ex: 1006',
        'min': 0,
        'max': 999999,
        'help': 'Channel bandwidth in kHz'
    },
    {
        'key': 'satSearchPat',
        'label': 'Search Pattern',
        'type': 'select',
        'options': ['spiral', 'raster', 'cross'],
        'placeholder': 'spiral',
        'help': 'Antenna search pattern for acquisition'
    }
]