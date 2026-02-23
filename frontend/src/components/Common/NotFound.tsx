import { Link } from "@tanstack/react-router"
import { Button } from "@/components/ui/button"

const NotFound = () => {
  return (
    <div
      className="flex min-h-screen items-center justify-center flex-col p-4 bg-background"
      data-testid="not-found"
    >
      <div className="flex items-center">
        <div className="flex flex-col ml-4 items-center justify-center p-4">
          <span className="text-6xl md:text-8xl font-light text-foreground/20 leading-none mb-4">
            404
          </span>
          <span className="text-xl font-medium text-foreground mb-2">页面未找到</span>
        </div>
      </div>

      <p className="text-sm text-muted-foreground mb-6 text-center">
        抱歉，您访问的页面不存在或已被移除。
      </p>
      <Link to="/">
        <Button variant="default" className="h-9">
          返回首页
        </Button>
      </Link>
    </div>
  )
}

export default NotFound
