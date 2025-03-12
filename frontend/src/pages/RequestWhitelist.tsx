import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";

export default function RequestWhitelist() {
  const navigate = useNavigate();
  
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-gray-50">
      <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-md">
        <h1 className="text-2xl font-bold text-center mb-6">Access Required</h1>
        <p className="text-gray-700 mb-6">
          Your account is not whitelisted to use this application. Please contact your administrator
          to request access.
        </p>
        <div className="flex justify-center">
          <Button onClick={() => navigate("/login")}>Return to Login</Button>
        </div>
      </div>
    </div>
  );
}