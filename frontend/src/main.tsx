// import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import '@fortawesome/fontawesome-free/css/all.min.css';
import { registerServiceWorker } from './lib/pwa';

// Register service worker for PWA functionality
registerServiceWorker();

createRoot(document.getElementById('root')!).render(
  // <StrictMode>
    <App />
  // </StrictMode>,
)
