import {
  MessageSquare,
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
  useSidebar,
} from "@/components/ui/sidebar";
import { Link } from "react-router-dom";
import { useChatContext } from "@/layout";

// // Menu items.
// const items = [
//   // {
//   //   title: "Home",
//   //   url: "#",
//   //   icon: Home,
//   // },
//   // {
//   //   title: "Inbox",
//   //   url: "#",
//   //   icon: Inbox,
//   // },
//   // {
//   //   title: "Calendar",
//   //   url: "#",
//   //   icon: Calendar,
//   // },
//   // {
//   //   title: "Search",
//   //   url: "#",
//   //   icon: Search,
//   // },
//   {
//     title: "Settings",
//     url: "/settings",
//     icon: Settings,
//   },
// ];





export function AppSidebar() {


  const { chats } = useChatContext();
  const { setOpenMobile } = useSidebar();

  
  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <div className="flex items-center justify-between p-3">
            <SidebarGroupLabel className="text-base font-medium">Chats</SidebarGroupLabel>
            <a href="/">
              <button className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors">
                + New Chat
              </button>
            </a>
          </div>
          <SidebarGroupContent>
            <SidebarMenu className="space-y-1 max-h-[70vh] overflow-y-auto scrollbar">
              {chats.map((chat) => (
                <SidebarMenuItem key={chat.id}>
                  <SidebarMenuButton asChild>
                    <Link
                      to={`/chat/${chat.id}`}
                      onClick={() => setOpenMobile(false)}
                      className="flex items-center gap-2 px-3 py-2 text-base md:text-sm font-medium text-gray-700 dark:text-gray-200 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white transition-colors"
                    >
                      <MessageSquare className="h-5 w-5 md:h-4 md:w-4" />
                      <span className="truncate">{chat.title}</span>
                    </Link>
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
