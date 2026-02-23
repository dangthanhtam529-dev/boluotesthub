import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import {
  BarChart3,
  Bug,
  CalendarClock,
  Bell,
  FileText,
  FolderKanban,
  Home,
  ScrollText,
  Settings,
  Shield,
  Zap,
} from "lucide-react"

import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"

const mainItems = [
  { icon: Home, title: "首页", path: "/" },
  { icon: FolderKanban, title: "项目管理", path: "/projects" },
  { icon: FileText, title: "测试用例", path: "/items" },
  { icon: Zap, title: "测试执行", path: "/executions" },
  { icon: Bug, title: "缺陷管理", path: "/defects" },
  { icon: BarChart3, title: "测试报告", path: "/reports" },
]

const moreItems = [
  { icon: CalendarClock, title: "定时任务", path: "/scheduled-tasks" },
  { icon: Bell, title: "通知", path: "/notifications" },
  { icon: ScrollText, title: "审计日志", path: "/audit-logs" },
  { icon: Settings, title: "设置", path: "/settings" },
]

const adminItems = [
  { icon: Shield, title: "用户管理", path: "/admin" },
]

export function Main() {
  const { isMobile, setOpenMobile } = useSidebar()
  const { user } = useAuth()
  const router = useRouterState()
  const currentPath = router.location.pathname

  const handleMenuClick = () => {
    if (isMobile) {
      setOpenMobile(false)
    }
  }

  return (
    <>
      <NavGroup label="主要功能" items={mainItems} currentPath={currentPath} onClick={handleMenuClick} />
      <NavGroup label="更多" items={moreItems} currentPath={currentPath} onClick={handleMenuClick} />
      {user?.is_superuser && (
        <NavGroup label="管理" items={adminItems} currentPath={currentPath} onClick={handleMenuClick} />
      )}
    </>
  )
}

function NavGroup({
  label,
  items,
  currentPath,
  onClick,
}: {
  label: string
  items: { icon: React.ComponentType<{ className?: string }>; title: string; path: string }[]
  currentPath: string
  onClick: () => void
}) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel className="text-xs text-muted-foreground/70 font-normal">
        {label}
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const isActive =
              item.path === "/"
                ? currentPath === "/"
                : currentPath.startsWith(item.path)

            return (
              <SidebarMenuItem key={item.path}>
                <SidebarMenuButton
                  tooltip={item.title}
                  isActive={isActive}
                  asChild
                >
                  <RouterLink to={item.path} onClick={onClick}>
                    <item.icon className="size-4" />
                    <span>{item.title}</span>
                  </RouterLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}
