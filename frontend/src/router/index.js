import { createRouter, createWebHashHistory } from 'vue-router'
import Overview from '../components/Overview.vue'
// import Stats from '../components/Stats.vue'
import Config from '../components/Config.vue'
import Tools from '../components/Tools.vue'
import ConfigMgmt from '../components/ConfigMgmt.vue'
import TleMgmt from '../components/TleMgmt.vue'
import Satellite from '../components/SatelliteList.vue'
import NetworkStats from '../components/NetworkStats.vue'
import Docs from '../components/Docs.vue'
import CliConsole from '../components/CliConsole.vue'
import SmartUpload from '../components/SmartUpload.vue'
import UnifiedLogs from '../components/UnifiedLogs.vue'

const routes = [
  {
    path: '/',
    name: 'overview',
    component: Overview
  },
  // { path: '/stats', name: 'stats', component: Stats },
  // Configuration routes
  {
    path: '/config/system',
    name: 'config-system',
    component: Config,
    props: { section: 'system' }
  },
  {
    path: '/config/network',
    name: 'config-network',
    component: Config,
    props: { section: 'network' }
  },
  {
    path: '/config/sensors',
    name: 'config-sensors',
    component: Config,
    props: { section: 'sensors' }
  },
  {
    path: '/config/esa',
    name: 'config-esa',
    component: Config,
    props: { section: 'esa' }
  },
  {
    path: '/config/location',
    name: 'config-location',
    component: Config,
    props: { section: 'location' }
  },
  {
    path: '/config/advanced',
    name: 'config-advanced',
    component: Config,
    props: { section: 'advanced' }
  },
  {
    path: '/config/satellite',
    name: 'config-satellite',
    component: Satellite
  },
  {
    path: '/satellite',
    redirect: '/config/satellite'
  },
  // Tools routes
  {
    path: '/tools/config-mgmt',
    name: 'tools-config-mgmt',
    component: ConfigMgmt
  },
  {
    path: '/tools/tle-mgmt',
    name: 'tools-tle-mgmt',
    component: TleMgmt
  },
  {
    path: '/tools/calibration',
    name: 'tools-calibration',
    component: Tools,
    props: { section: 'calibration' }
  },
  {
    path: '/tools/events',
    name: 'tools-events',
    component: Tools,
    props: { section: 'events' }
  },
  {
    path: '/tools/logs',
    name: 'tools-logs',
    component: Tools,
    props: { section: 'logs' }
  },
  {
    path: '/tools/upgrade',
    name: 'tools-upgrade',
    component: Tools,
    props: { section: 'upgrade' }
  },
  {
    path: '/tools/reboot',
    name: 'tools-reboot',
    component: Tools,
    props: { section: 'reboot' }
  },
  {
    path: '/tools/network',
    name: 'tools-network',
    component: NetworkStats
  },
  {
    path: '/docs',
    name: 'docs',
    component: Docs
  },
  // Hidden dev console — URL-only (#/debug/cli), not linked in any nav menu.
  {
    path: '/debug/cli',
    name: 'debug-cli',
    component: CliConsole
  },
  // Hidden smart-upload demo — URL-only (#/debug/upload), not linked in any nav.
  {
    path: '/debug/upload',
    name: 'debug-upload',
    component: SmartUpload
  },
  // Hidden unified logs+events demo — URL-only (#/debug/logs), not linked in any nav.
  {
    path: '/debug/logs',
    name: 'debug-logs',
    component: UnifiedLogs
  },
  // Catch all - redirect to overview
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router