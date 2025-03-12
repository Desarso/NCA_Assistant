import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from 'firebase/auth';
import { auth, onAuthStateChanged } from './firebase';
import { useIsMobile } from '@/hooks/use-mobile';

interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  isWhitelisted: boolean;
  // biometricsSupported: boolean;
  // requiresBiometricAuth: boolean;
  // verifyBiometrics: () => Promise<boolean>;
  // setBiometricVerified: (verified: boolean) => void;
}

const AuthContext = createContext<AuthContextType>({ 
  currentUser: null, 
  loading: true,
  isWhitelisted: false
});

  // biometricsSupported: false,
    // requiresBiometricAuth: false,
    // verifyBiometrics: async () => false,
    // setBiometricVerified: () => {},

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isWhitelisted, setIsWhitelisted] = useState(false);
  // const [biometricsSupported, setBiometricsSupported] = useState(false);
  // const [requiresBiometricAuth, setRequiresBiometricAuth] = useState(false);
  const isMobile = useIsMobile();

  // Set up biometric support check
  // useEffect(() => {
  //   const checkBiometricSupport = async () => {
  //     if (isMobile) {
  //       const supported = await isBiometricSupported();
  //       setBiometricsSupported(supported);
  //     }
  //   };
    
  //   checkBiometricSupport();
  // }, [isMobile]);

  // Set up auth state listener
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setCurrentUser(user);
      
      if (user) {
        try {
          // Get the ID token with fresh claims
          const idTokenResult = await user.getIdTokenResult(true);
          
          // Check if user has the whitelisted claim
          const whitelisted = !!idTokenResult.claims.whitelisted;
          setIsWhitelisted(whitelisted);
          
          // If user is whitelisted and on mobile device, try to set up passkey
          // if (whitelisted && isMobile && biometricsSupported) {
          //   const hasPasskey = localStorage.getItem('passkey_created') === 'true';
            
          //   if (!hasPasskey) {
          //     // Try to create a passkey for this user
          //     await createPasskey(user.uid, user.email || user.uid);
          //   }
            
          //   // User will need biometric verification when returning to the app
          //   setRequiresBiometricAuth(true);
          // }
        } catch (error) {
          console.error("Error fetching user claims:", error);
          setIsWhitelisted(false);
        }
      } else {
        setIsWhitelisted(false);
        // setRequiresBiometricAuth(false);
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, [isMobile]);

  // Function to verify user with biometrics
  // const verifyBiometrics = async (): Promise<boolean> => {
  //   if (!biometricsSupported || !currentUser) {
  //     return false;
  //   }
    
  //   try {
  //     const verified = await verifyWithPasskey();
  //     if (verified) {
  //       setRequiresBiometricAuth(false);
  //     }
  //     return verified;
  //   } catch (error) {
  //     console.error('Error verifying with biometrics:', error);
  //     return false;
  //   }
  // };
  
  // // Function to manually set biometric verification status
  // const setBiometricVerified = (verified: boolean) => {
  //   setRequiresBiometricAuth(!verified);
  // };

  const value = {
    currentUser,
    loading,
    isWhitelisted,
    // biometricsSupported,
    // requiresBiometricAuth,
    // verifyBiometrics,
    // setBiometricVerified
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}