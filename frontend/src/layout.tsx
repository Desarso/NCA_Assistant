import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./components/app-sidebar";
import { PWAInstallButton } from "./components/pwa-install-button";
import { useEffect, useState, createContext, useContext } from "react";
import { useIsMobile } from "./hooks/use-mobile";
import { ModeToggle } from "./components/mode-toogle";
import AvatarDropdown from "./components/avatar-dropdown";

// Move interfaces outside the component
interface Conversation {
  id: number;
  title: string;
}

interface ChatContextType {
  chats: { id: string; title: string }[];
  fetchConversations: () => Promise<void>;
}

// Create the context
export const ChatContext = createContext<ChatContextType>({
  chats: [],
  fetchConversations: async () => {}
});

// Create a custom hook for using the context
export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const isMobile = useIsMobile();
  const HOST = import.meta.env.VITE_CHAT_HOST;

  const [chats, setChats] = useState<{id: string, title: string}[]>([]);

  
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
      
      const response = await authFetch(`${HOST}/api/v1/chats/users/${user.uid}/conversations`);
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

  useEffect(() => {
  
    fetchConversations();
  }, []);
    
  return (
    <ChatContext.Provider value={{ chats, fetchConversations }}>
      <SidebarProvider>
        <div className="flex h-screen w-full">
          <AppSidebar/>
          <main className="flex flex-col flex-1 h-screen overflow-hidden">
            <header className="flex items-center justify-between p-4 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3">
                <SidebarTrigger className="hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg p-2 transition-colors [&_svg:not([class*='size-'])]:size-7! md:[&_svg:not([class*='size-'])]:size-5!">
                </SidebarTrigger>
                <h1 className="text-xl font-semibold text-gray-800 dark:text-gray-200 md:text-lg">
                  NCA Assistant
                </h1>
              </div>
              <div className="flex items-center gap-3">
                <ModeToggle />
                <AvatarDropdown />
              </div>
              {isMobile && (
                <PWAInstallButton className="ml-auto" />
              )}
            </header>
            <div className="flex-1 overflow-auto">
              {children}
            </div>
          </main>
        </div>
      </SidebarProvider>
    </ChatContext.Provider>
  );
}
