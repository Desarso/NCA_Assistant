import ChatWindow from "./aichat/pages/ChatWindow";
import SettingsPage from "./aichat/pages/SettingsPage";
import Login from "./pages/Login";
import RequestWhitelist from "./pages/RequestWhitelist";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./index.css";
import Layout from "./layout";
import PrivateRoute from "./components/PrivateRoute";
import { AuthProvider } from "./lib/auth-context";

function AppRoutes() {
  // const { setBiometricVerified } = useAuth();
  return (
    <>
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