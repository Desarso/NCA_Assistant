import { useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useAuth } from '@/lib/auth-context';

export default function RequestWhitelist() {
  const navigate = useNavigate();
  const { currentUser, isWhitelisted, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      if (!currentUser) {
        // If not logged in, redirect to login
        navigate('/login');
      } else if (isWhitelisted) {
        // If already whitelisted, redirect to home
        navigate('/');
      }
    }
  }, [currentUser, isWhitelisted, loading, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900">
      <div className="w-full max-w-md p-8 space-y-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Access Required</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Your account is not whitelisted to use this application. Please contact your administrator
            to request access.
          </p>
        </div>
        
        <div className="flex justify-center">
          <Button 
            onClick={() => navigate("/login")}
            className="w-full flex items-center justify-center gap-2 bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 dark:bg-gray-700 dark:text-white dark:border-gray-600 dark:hover:bg-gray-600"
          >
            Return to Login
          </Button>
        </div>
      </div>
    </div>
  );
}