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
          <div className="flex items-center justify-between p-4 md:p-4">
            <SidebarGroupLabel className="text-lg md:text-base">Chats</SidebarGroupLabel>
            <a href="/">
              <button className="p-3 md:p-2 text-2xl md:text-sm font-medium text-gray-300 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors">
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
                      className="flex items-center text-2xl!
                      [&>svg]:size-8!
                      md:[&>svg]:size-5!
                      gap-3 md:gap-2 px-4 md:px-3 py-7 md:py-2 md:text-sm! font-medium text-gray-300 rounded-md hover:bg-gray-100 hover:text-gray-900 transition-colors"
                    >
                      <MessageSquare className="w-6 h-6 md:w-4 md:h-4" />
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
                    <a href={item.url} className="text-2xl! md:text-base!
                    py-7
                    [&>svg]:size-8!
                    md:[&>svg]:size-5!
                    md:py-2
                    ">
                      <item.icon className="w-8 h-8 md:w-4 md:h-4
                      
                      "
                      size={20}
                      />
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
