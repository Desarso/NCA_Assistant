import { useState, useEffect, useCallback } from 'react';
import { useIsMobile } from './use-mobile';

interface AppVisibilityHook {
  wasHidden: boolean;
  resetVisibility: () => void;
}

export function useAppVisibility(): AppVisibilityHook {
  const [wasHidden, setWasHidden] = useState(false);
  const isMobile = useIsMobile();

  const handleVisibilityChange = useCallback(() => {
    if (document.visibilityState === 'visible' && document.hidden === false) {
      // App has become visible after being hidden
      setWasHidden(true);
    }
  }, []);

  const resetVisibility = useCallback(() => {
    setWasHidden(false);
  }, []);

  useEffect(() => {
    // Only add listeners if on mobile
    if (isMobile) {
      document.addEventListener('visibilitychange', handleVisibilityChange);
      window.addEventListener('focus', handleVisibilityChange);
      
      return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        window.removeEventListener('focus', handleVisibilityChange);
      };
    }
  }, [handleVisibilityChange, isMobile]);

  return { wasHidden, resetVisibility };
}