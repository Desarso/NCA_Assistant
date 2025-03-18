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
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="w-full max-w-md p-8 space-y-8 bg-card rounded-lg shadow-lg border border-border">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground">Access Required</h1>
          <p className="mt-2 text-muted-foreground">
            Your account is not whitelisted to use this application. Please contact your administrator
            to request access.
          </p>
        </div>
        
        <div className="flex justify-center">
          <Button 
            onClick={() => navigate("/login")}
            variant="outline"
            className="w-full"
          >
            Return to Login
          </Button>
        </div>
      </div>
    </div>
  );
}