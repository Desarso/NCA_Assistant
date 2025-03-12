import { Button } from '@/components/ui/button';
import { usePWAInstallPrompt } from '@/lib/pwa';
import { Download } from 'lucide-react';

interface PWAInstallButtonProps {
  className?: string;
}

export function PWAInstallButton({ className }: PWAInstallButtonProps) {
  const { isInstallable, isInstalled, promptInstall } = usePWAInstallPrompt();
  
  // Don't show anything if already installed or can't be installed
  if (isInstalled || !isInstallable) {
    return null;
  }
  
  const handleInstall = async () => {
    const installed = await promptInstall();
    if (installed) {
      console.log('App was installed successfully');
    }
  };
  
  return (
    <Button 
      onClick={handleInstall} 
      variant="outline" 
      size="sm"
      className={className}
    >
      <Download className="h-4 w-4 mr-2" />
      Install App
    </Button>
  );
}