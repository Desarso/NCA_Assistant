import ChatWindow from "./aichat/pages/ChatWindow";
import SettingsPage from "./aichat/pages/SettingsPage";
import Login from "./pages/Login";
import RequestWhitelist from "./pages/RequestWhitelist";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./index.css";
import Layout from "./layout";
import PrivateRoute from "./components/PrivateRoute";
import { AuthProvider } from "./lib/auth-context";
import { BiometricAuthModal } from "./components/biometric-auth-modal";
import { SplashScreen } from "./components/splash-screen";
import { useEffect, useState } from "react";
import { useAuth } from "./lib/auth-context";
import { useIsMobile } from "./hooks/use-mobile";

function AppRoutes() {
  const { setBiometricVerified } = useAuth();
  const isMobile = useIsMobile();
  const [showSplash, setShowSplash] = useState(true);
  
  // Show splash screen only on standalone mode (when installed)
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                      (window.navigator as any).standalone || 
                      document.referrer.includes('android-app://');

  // Hide splash screen after delay
  useEffect(() => {
    if (showSplash) {
      const timer = setTimeout(() => {
        setShowSplash(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [showSplash]);

  // Listen for app visibility changes to trigger biometric auth
  // useEffect(() => {
  //     // App was hidden and is now visible again, require biometric auth
  //     setBiometricVerified(false);
  // }, []);

  return (
    <>
      {/* Only show splash screen on mobile when running as installed app */}
      {isMobile && isStandalone && showSplash && (
        <SplashScreen />
      )}
      
      <BiometricAuthModal />
      
      {/* Don't render routes until splash is done on installed app */}
      {(!isMobile || !isStandalone || !showSplash) && (
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/request-whitelist" element={<RequestWhitelist />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout>
                  <ChatWindow />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route
            path="/chat/:id"
            element={
              <PrivateRoute>
                <Layout>
                  <ChatWindow id={window.location.pathname.split('/').pop()} />
                </Layout>
              </PrivateRoute>
            }
          />
          <Route 
            path="/settings" 
            element={
              <PrivateRoute>
                <Layout>
                  <SettingsPage />
                </Layout>
              </PrivateRoute>
            } 
          />
        </Routes>
      )}
    </>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;