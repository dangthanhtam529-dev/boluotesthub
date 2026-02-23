import { Appearance } from "@/components/Common/Appearance"

interface AuthLayoutProps {
  children: React.ReactNode
}

export function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* 右上角主题切换 */}
      <div className="fixed top-5 right-5 z-10">
        <Appearance />
      </div>

      <div className="w-full max-w-sm">
        {/* 品牌区 - 轻盈简洁 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
            <svg
              className="w-6 h-6 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 007.92 12.446A9 9 0 1112 2.992z"
              />
            </svg>
          </div>
          <h1 className="text-xl font-medium text-foreground tracking-wide">
            测试管理平台
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            简化流程 · 提升效率
          </p>
        </div>

        {/* 登录卡片 */}
        <div className="bg-card rounded-2xl border border-border p-6 shadow-sm">
          {children}
        </div>

        {/* 底部 */}
        <p className="text-center text-xs text-muted-foreground/60 mt-6">
          © {new Date().getFullYear()} 测试管理平台
        </p>
      </div>
    </div>
  )
}
