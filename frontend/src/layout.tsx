import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./components/app-sidebar";
import { PWAInstallButton } from "./components/pwa-install-button";
import { useEffect, useState } from "react";
import { useIsMobile } from "./hooks/use-mobile";

export default function Layout({ children }: { children: React.ReactNode }) {
  const isMobile = useIsMobile();

  interface Conversation {
    id: number;
    title: string;
    created_at: string;
    updated_at: string;
    user_id: number;
  }

  const [chats, setChats] = useState<{id: string, title: string}[]>([]);

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        // Import here to avoid circular dependency
        const { authFetch } = await import('@/lib/utils');
        const { auth } = await import('@/lib/firebase');
        
        // Get current user UID
        const user = auth.currentUser;
        if (!user) {
          console.error('User not authenticated');
          return;
        }
        
        const response = await authFetch(`http://localhost:8000/users/${user.uid}/conversations`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data.status === "success" && Array.isArray(data.conversations)) {
          setChats(data.conversations.map((conv: Conversation) => ({
            id: conv.id.toString(),
            title: conv.title
          })));
        }
      } catch (error) {
        console.error('Failed to fetch conversations:', error);
      }
    };

    fetchConversations();
  }, []);
    
  return (
    <SidebarProvider>
      <AppSidebar 
        chats={chats}
      />
      <main className="flex flex-col h-screen w-full">
        <div className="flex items-center justify-between p-2 bg-gray-200 dark:bg-gray-700">
          <div className="flex items-center">
            <SidebarTrigger />
            <h1 className="text-xl font-semibold ml-2 text-gray-800 dark:text-gray-200">NCA Assistant</h1>
          </div>
          {isMobile && <PWAInstallButton className="ml-auto" />}
        </div>
        {children}
      </main>
    </SidebarProvider>
  );
}
