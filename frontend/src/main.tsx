import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const isCapacitorNative = Boolean(
  (window as { Capacitor?: { isNativePlatform?: () => boolean } }).Capacitor?.isNativePlatform?.()
);

// Register PWA Service Worker in production web (skip inside native Capacitor WebView)
if (!isCapacitorNative && 'serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => console.log('ServiceWorker registered successfully: ', reg.scope))
      .catch((err) => console.error('ServiceWorker registration failed: ', err));
  });
}

if (isCapacitorNative) {
  import('@capacitor/status-bar')
    .then(({ StatusBar, Style }) => {
      StatusBar.setStyle({ style: Style.Dark }).catch(() => {});
      StatusBar.setBackgroundColor({ color: '#111414' }).catch(() => {});
    })
    .catch(() => {});
  import('@capacitor/splash-screen')
    .then(({ SplashScreen }) => {
      SplashScreen.hide().catch(() => {});
    })
    .catch(() => {});
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

