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

  const HOST = import.meta.env.VITE_CHAT_HOST;

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
        
        const response = await authFetch(`${HOST}/users/${user.uid}/conversations`);
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
      <AppSidebar chats={chats} />
      <main className="flex flex-col h-screen w-full">
        <header className="flex items-center justify-between p-4 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <SidebarTrigger className="hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg p-2 transition-colors [&_svg:not([class*='size-'])]:size-7! md:[&_svg:not([class*='size-'])]:size-5!">
            </SidebarTrigger>
            <h1 className="text-xl font-semibold text-gray-800 dark:text-gray-200 md:text-lg">
              NCA Assistant
            </h1>
          </div>
          {isMobile && (
            <PWAInstallButton className="ml-auto" />
          )}
        </header>
        {children}
      </main>
    </SidebarProvider>
  );
}
