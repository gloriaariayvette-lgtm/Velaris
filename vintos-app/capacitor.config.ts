import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'dev.vintos.app',
  appName: 'Vintos',
  webDir: 'src',

  server: {
    cleartext: true,
  },

  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 1500,
      backgroundColor: '#1C1E22',
      showSpinner: false,
    },
    LocalNotifications: {
      smallIcon: 'vintos_icon',
      iconColor: '#C96B3C',
    },
    BackgroundRunner: {
      label: 'dev.vintos.outreach-check',
      src: 'runners/outreach.js',
      event: 'checkOutreach',
      repeat: true,
      interval: 5, // minutes
      autoStart: true,
    },
  },

  // iOS specific
  ios: {
    contentInset: 'automatic',
    allowsLinkPreview: false,
    backgroundColor: '#1C1E22',
    preferredContentMode: 'mobile',
    // Allow cleartext HTTP to Tailscale
    limitsNavigationsToAppBoundDomains: false,
  },
};

export default config;
