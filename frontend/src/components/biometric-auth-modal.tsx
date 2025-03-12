import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';

export function BiometricAuthModal() {
  const { requiresBiometricAuth, verifyBiometrics, biometricsSupported } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Open modal if biometric auth is required
    if (requiresBiometricAuth && biometricsSupported) {
      setIsOpen(true);
      setError(null);
    } else {
      setIsOpen(false);
    }
  }, [requiresBiometricAuth, biometricsSupported]);

  const handleVerify = async () => {
    setIsVerifying(true);
    setError(null);
    
    try {
      const success = await verifyBiometrics();
      
      if (success) {
        setIsOpen(false);
      } else {
        setError('Verification failed. Please try again.');
      }
    } catch (err) {
      setError('An error occurred during verification.');
      console.error('Biometric verification error:', err);
    } finally {
      setIsVerifying(false);
    }
  };

  // Don't render if biometrics not supported or not required
  if (!biometricsSupported || !requiresBiometricAuth) {
    return null;
  }

  return (
    <Sheet open={isOpen} onOpenChange={() => {}}>
      <SheetContent side="bottom" className="h-[30vh]">
        <SheetHeader>
          <SheetTitle>Verify Your Identity</SheetTitle>
          <SheetDescription>
            Please verify your identity using your fingerprint or face ID to continue.
          </SheetDescription>
        </SheetHeader>
        
        <div className="flex flex-col items-center justify-center gap-4 py-8">
          {error && (
            <div className="text-sm font-medium text-destructive mb-2">
              {error}
            </div>
          )}
          
          <Button
            onClick={handleVerify}
            disabled={isVerifying}
            className="w-full max-w-xs"
          >
            {isVerifying ? 'Verifying...' : 'Use Fingerprint / Face ID'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}