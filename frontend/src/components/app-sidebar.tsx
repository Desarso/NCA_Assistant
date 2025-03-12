import {
  MessageSquare,
  Settings,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

// Menu items.
const items = [
  // {
  //   title: "Home",
  //   url: "#",
  //   icon: Home,
  // },
  // {
  //   title: "Inbox",
  //   url: "#",
  //   icon: Inbox,
  // },
  // {
  //   title: "Calendar",
  //   url: "#",
  //   icon: Calendar,
  // },
  // {
  //   title: "Search",
  //   url: "#",
  //   icon: Search,
  // },
  {
    title: "Settings",
    url: "/settings",
    icon: Settings,
  },
];

interface Chat {
  id: string;
  title: string;
}

export function AppSidebar({ chats }: { chats: Chat[] }) {
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <div className="flex items-center justify-between p-4">
            <SidebarGroupLabel>Chats</SidebarGroupLabel>
            <a href="/">
              <button className="p-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors">
                + New Chat
              </button>
            </a>
          </div>
          <SidebarGroupContent>
            <SidebarMenu
              className="max-h-[70vh] overflow-y-auto scrollbar"
            >
              {chats.map((chat) => (
                <SidebarMenuItem key={chat.id}
                  
                >
                  <SidebarMenuButton asChild>
                    <a
                      href={`/chat/${chat.id}`}
                      className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      <span className="truncate">{chat.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
            <SidebarMenu>
              {items.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <a href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
