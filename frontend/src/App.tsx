import ChatWindow from "./aichat/pages/ChatWindow";
import SettingsPage from "./pages/SettingsPage";
import Login from "./pages/Login";
import RequestWhitelist from "./pages/RequestWhitelist";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import "./index.css";
import Layout from "./layout";
import PrivateRoute from "./components/PrivateRoute";
import { AuthProvider } from "./lib/auth-context";
import Animation from "./pages/Animation";
import ProfilePage from "./pages/ProfilePage";

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
                <ChatWindow/>
              </Layout>
            </PrivateRoute>
          }
        />
        <Route
          path="/animation"
          element={
            <PrivateRoute>
              <Layout>
                <Animation />
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
        <Route
          path="/profile"
          element={
            <PrivateRoute>
              <Layout>
                <ProfilePage />
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
