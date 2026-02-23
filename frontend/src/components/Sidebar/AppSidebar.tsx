import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import { Main } from "@/components/Sidebar/Main"
import { User } from "@/components/Sidebar/User"

export default function AppSidebar() {
  return (
    <Sidebar collapsible="icon" variant="sidebar">
      <SidebarHeader className="p-4">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarSeparator />
      <SidebarContent className="px-2 py-1">
        <Main />
      </SidebarContent>
      <SidebarSeparator />
      <SidebarFooter className="p-2">
        <SidebarMenu>
          <SidebarAppearance />
        </SidebarMenu>
        <User />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
