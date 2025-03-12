import React from 'react';
import { registerSW } from 'virtual:pwa-register';
import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { UpdateNotification } from '@/components/update-notification';

// Container for update notification
let updateContainer: HTMLDivElement | null = null;
let notificationRoot: ReturnType<typeof createRoot> | null = null;

// Show update notification using portal
const showUpdateNotification = (updateFn: () => Promise<void>) => {
  try {
    // Cleanup existing notification if present
    if (notificationRoot) {
      notificationRoot.unmount();
      notificationRoot = null;
    }
    if (updateContainer && document.body.contains(updateContainer)) {
      document.body.removeChild(updateContainer);
      updateContainer = null;
    }
    
    // Create new container
    updateContainer = document.createElement('div');
    updateContainer.id = 'pwa-update-container';
    document.body.appendChild(updateContainer);

    // Create and store root
    notificationRoot = createRoot(updateContainer);
    notificationRoot.render(
      React.createElement(UpdateNotification, {
        onUpdate: async () => {
          try {
            await updateFn();
          } catch (error) {
            console.error('Error updating service worker:', error);
          } finally {
            if (notificationRoot) {
              notificationRoot.unmount();
              notificationRoot = null;
            }
            if (updateContainer && document.body.contains(updateContainer)) {
              document.body.removeChild(updateContainer);
              updateContainer = null;
            }
          }
        },
        onDismiss: () => {
          if (notificationRoot) {
            notificationRoot.unmount();
            notificationRoot = null;
          }
          if (updateContainer && document.body.contains(updateContainer)) {
            document.body.removeChild(updateContainer);
            updateContainer = null;
          }
        }
      })
    );
  } catch (error) {
    console.error('Error showing update notification:', error);
    // Cleanup on error
    if (notificationRoot) {
      notificationRoot.unmount();
      notificationRoot = null;
    }
    if (updateContainer && document.body.contains(updateContainer)) {
      document.body.removeChild(updateContainer);
      updateContainer = null;
    }
  }
};

// Initialize PWA update checker
export const registerServiceWorker = () => {
  if (typeof window === 'undefined') return () => Promise.resolve();
  
  const updateSW = registerSW({
    onNeedRefresh() {
      showUpdateNotification(() => updateSW(true));
    },
    onOfflineReady() {
      console.log('App ready to work offline');
    },
    immediate: true
  });
  
  return updateSW;
};

// Add proper type for BeforeInstallPromptEvent
interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

// Hook for PWA installation prompt
export const usePWAInstallPrompt = () => {
  const [installPrompt, setInstallPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    let mounted = true;

    // Check if app is already installed
    const checkInstalled = () => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                          (window.navigator as any).standalone === true;
      if (isStandalone && mounted) {
        setIsInstalled(true);
        return true;
      }
      return false;
    };

    // Handle the install prompt event
    const handleBeforeInstallPrompt = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      if (mounted) {
        setInstallPrompt(e);
      }
    };

    // Check if already installed
    const isAlreadyInstalled = checkInstalled();
    
    if (!isAlreadyInstalled) {
      window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt as EventListener);
    }
    
    const handleAppInstalled = () => {
      if (mounted) {
        setIsInstalled(true);
        setInstallPrompt(null);
      }
    };
    
    window.addEventListener('appinstalled', handleAppInstalled);

    // Cleanup
    return () => {
      mounted = false;
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt as EventListener);
      window.removeEventListener('appinstalled', handleAppInstalled);
    };
  }, []);

  const promptInstall = async () => {
    if (!installPrompt) return false;
    
    try {
      await installPrompt.prompt();
      const choiceResult = await installPrompt.userChoice;
      return choiceResult.outcome === 'accepted';
    } catch (error) {
      console.error('Error installing PWA:', error instanceof Error ? error.message : 'Unknown error');
      return false;
    }
  };

  return { 
    isInstallable: !!installPrompt, 
    isInstalled, 
    promptInstall 
  };
};