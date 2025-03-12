import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./components/app-sidebar";
import { useEffect, useState } from "react";

export default function Layout({ children }: { children: React.ReactNode }) {


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
        const response = await fetch('http://localhost:8000/users/1/conversations');
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
        <div className="flex items-center p-2 bg-gray-200 dark:bg-gray-700">
          <SidebarTrigger />
          <div>
          <h1 className="text-xl font-semibold ml-2 text-gray-800 dark:text-gray-200">NCA Assistant</h1>
          </div>
        </div>
        {children}
      </main>
    </SidebarProvider>
  );
}
