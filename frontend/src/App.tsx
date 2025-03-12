import ChatWindow from "./aichat/pages/ChatWindow";
import SettingsPage from "./aichat/pages/SettingsPage";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import "./index.css";
import React, { useState } from "react";
import Layout from "./layout";

function App() {
  const [selectedConversation, setSelectedConversation] = useState<
    string | null
  >(null);
  const [isOpen, setIsOpen] = useState(true);

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };


  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <Layout>
                <ChatWindow />
            </Layout>
          }
        />
          <Route
            path="/chat/:id"
            element={
              <Layout>
                  <ChatWindow id={window.location.pathname.split('/').pop()} />
              </Layout>
            }
          />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
