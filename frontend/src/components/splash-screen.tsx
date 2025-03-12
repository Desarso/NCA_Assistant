import { useEffect, useState } from 'react';

interface SplashScreenProps {
  minimumDisplayTime?: number;
}

export function SplashScreen({ minimumDisplayTime = 1000 }: SplashScreenProps) {
  const [show, setShow] = useState(true);

  useEffect(() => {
    // Display splash screen for at least minimumDisplayTime
    const timer = setTimeout(() => {
      setShow(false);
    }, minimumDisplayTime);

    return () => clearTimeout(timer);
  }, [minimumDisplayTime]);

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-gray-900">
      <div className="w-24 h-24 mb-4 rounded-lg bg-blue-500 animate-pulse flex items-center justify-center">
        <svg 
          xmlns="http://www.w3.org/2000/svg" 
          viewBox="0 0 24 24"
          className="w-16 h-16 text-white"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="4" />
        </svg>
      </div>
      <h1 className="text-xl font-bold text-white">NCA Assistant</h1>
      <p className="text-gray-400 mt-2 text-sm">Starting up...</p>
    </div>
  );
}