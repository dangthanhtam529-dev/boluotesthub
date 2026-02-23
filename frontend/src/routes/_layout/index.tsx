import { createFileRoute, Link as RouterLink } from "@tanstack/react-router"
import {
  Activity,
  BarChart3,
  CheckCircle2,
  Clock,
  FileText,
  XCircle,
  Zap,
} from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "首页 - 测试管理平台",
      },
    ],
  }),
})

function Dashboard() {
  const { user: currentUser } = useAuth()

  const stats = {
    totalCases: 1284,
    passed: 956,
    failed: 89,
    pending: 239,
    todayExecutions: 47,
    passRate: 91.5,
  }

  const greeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return "早上好"
    if (hour < 18) return "下午好"
    return "晚上好"
  }

  return (
    <div className="space-y-8">
      {/* 欢迎区 */}
      <div>
        <h1 className="text-xl font-medium text-foreground">
          {greeting()}，{currentUser?.full_name || "用户"}
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          以下是项目的最新状态概览
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="用例总数"
          value={stats.totalCases}
          icon={<FileText className="w-4 h-4" />}
          color="primary"
        />
        <StatCard
          label="通过"
          value={stats.passed}
          icon={<CheckCircle2 className="w-4 h-4" />}
          color="green"
        />
        <StatCard
          label="失败"
          value={stats.failed}
          icon={<XCircle className="w-4 h-4" />}
          color="red"
        />
        <StatCard
          label="待处理"
          value={stats.pending}
          icon={<Clock className="w-4 h-4" />}
          color="amber"
        />
      </div>

      {/* 下半区 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* 通过率 */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              通过率
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-light text-primary">
                {stats.passRate}%
              </span>
            </div>
            <div className="mt-4 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary/70 rounded-full transition-all"
                style={{ width: `${stats.passRate}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              基于 {stats.passed + stats.failed} 个已执行用例
            </p>
          </CardContent>
        </Card>

        {/* 今日概览 */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              今日概览
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">今日执行</span>
              <span className="text-2xl font-light text-primary">
                {stats.todayExecutions}
              </span>
            </div>
            <div className="h-px bg-border" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">待处理</span>
              <span className="text-2xl font-light text-chart-3">
                {stats.pending}
              </span>
            </div>
            <div className="h-px bg-border" />
            <div className="flex items-center justify-between">
              <span className="text-sm text-foreground">累计通过</span>
              <span className="text-2xl font-light text-primary">
                {stats.passed}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* 快捷操作 */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              快捷操作
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <QuickAction
              to="/executions"
              icon={<Zap className="w-4 h-4 text-primary" />}
              title="新建执行"
              desc="创建测试执行任务"
            />
            <QuickAction
              to="/reports"
              icon={<BarChart3 className="w-4 h-4 text-chart-2" />}
              title="查看报告"
              desc="测试报告与统计"
            />
            <QuickAction
              to="/defects"
              icon={<XCircle className="w-4 h-4 text-destructive" />}
              title="缺陷管理"
              desc="查看和处理缺陷"
            />
            <QuickAction
              to="/projects"
              icon={<Activity className="w-4 h-4 text-chart-4" />}
              title="项目管理"
              desc="管理测试项目"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/* 统计卡片组件 */
function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string
  value: number
  icon: React.ReactNode
  color: "primary" | "green" | "red" | "amber"
}) {
  const colorMap = {
    primary: "bg-primary/8 text-primary",
    green: "bg-emerald-500/8 text-emerald-600 dark:text-emerald-400",
    red: "bg-red-500/8 text-red-500 dark:text-red-400",
    amber: "bg-amber-500/8 text-amber-600 dark:text-amber-400",
  }

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-muted-foreground">{label}</span>
          <div className={`p-1.5 rounded-lg ${colorMap[color]}`}>{icon}</div>
        </div>
        <p className="text-2xl font-light text-foreground">{value}</p>
      </CardContent>
    </Card>
  )
}

/* 快捷操作项 */
function QuickAction({
  to,
  icon,
  title,
  desc,
}: {
  to: string
  icon: React.ReactNode
  title: string
  desc: string
}) {
  return (
    <RouterLink
      to={to}
      className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-muted/50 transition-colors"
    >
      <div className="p-2 bg-accent/60 rounded-lg">{icon}</div>
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">{desc}</p>
      </div>
    </RouterLink>
  )
}
