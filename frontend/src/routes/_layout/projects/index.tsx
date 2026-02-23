import { createFileRoute, Link } from "@tanstack/react-router"
import { useState, useEffect } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api"

interface Project {
  id: string
  name: string
  description: string | null
  apifox_project_id: string | null
  owner_id: string
  is_active: boolean
  last_sync_at: string | null
  created_at: string | null
  updated_at: string | null
  collection_count: number
  execution_count: number
}

interface ProjectsResponse {
  data: Project[]
  count: number
}

function ProjectsListPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editProject, setEditProject] = useState<Project | null>(null)
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncProjectId, setSyncProjectId] = useState<string | null>(null)
  const [syncToken, setSyncToken] = useState("")
  const [syncing, setSyncing] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    apifox_project_id: "",
  })

  const loadProjects = async () => {
    try {
      setLoading(true)
      const res = await apiGet<ProjectsResponse>("/api/v1/projects/")
      setProjects(res.data || [])
    } catch (e: any) {
      toast.error(e.message || "加载项目失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast.error("请输入项目名称")
      return
    }
    try {
      await apiPost("/api/v1/projects/", {
        name: formData.name,
        description: formData.description || null,
        apifox_project_id: formData.apifox_project_id || null,
      })
      toast.success("项目创建成功")
      setCreateDialogOpen(false)
      setFormData({ name: "", description: "", apifox_project_id: "" })
      loadProjects()
    } catch (e: any) {
      toast.error(e.message || "创建失败")
    }
  }

  const handleUpdate = async () => {
    if (!editProject) return
    try {
      await apiPut(`/api/v1/projects/${editProject.id}`, {
        name: formData.name,
        description: formData.description || null,
        apifox_project_id: formData.apifox_project_id || null,
      })
      toast.success("项目更新成功")
      setEditProject(null)
      setFormData({ name: "", description: "", apifox_project_id: "" })
      loadProjects()
    } catch (e: any) {
      toast.error(e.message || "更新失败")
    }
  }

  const handleDelete = async (projectId: string) => {
    if (!confirm("确定要删除这个项目吗？")) return
    try {
      await apiDelete(`/api/v1/projects/${projectId}`)
      toast.success("项目删除成功")
      loadProjects()
    } catch (e: any) {
      toast.error(e.message || "删除失败")
    }
  }

  const handleSync = (projectId: string) => {
    setSyncProjectId(projectId)
    setSyncToken("")
    setSyncDialogOpen(true)
  }

  const doSync = async () => {
    if (!syncProjectId) return
    try {
      setSyncing(true)
      const tokenQuery = syncToken ? `?access_token=${encodeURIComponent(syncToken)}` : ""
      await apiPost(`/api/v1/projects/${syncProjectId}/sync${tokenQuery}`)
      toast.success("同步成功")
      setSyncDialogOpen(false)
      loadProjects()
    } catch (e: any) {
      toast.error(e.message || "同步失败")
    } finally {
      setSyncing(false)
    }
  }

  const openEditDialog = (project: Project) => {
    setEditProject(project)
    setFormData({
      name: project.name,
      description: project.description || "",
      apifox_project_id: project.apifox_project_id || "",
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">项目管理</h1>
          <p className="text-muted-foreground mt-1">管理测试项目和 Apifox 集成</p>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)}>创建项目</Button>
      </div>

      {loading ? (
        <div className="text-center py-10 text-muted-foreground">加载中...</div>
      ) : projects.length === 0 ? (
        <Card className="border border-border">
          <CardContent className="py-10 text-center text-muted-foreground">
            暂无项目，点击"创建项目"开始
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Card
              key={project.id}
              className="border border-border hover:shadow-md transition-shadow"
            >
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{project.name}</CardTitle>
                    <CardDescription className="mt-1">
                      {project.description || "暂无描述"}
                    </CardDescription>
                  </div>
                  {!project.is_active && (
                    <span className="px-2 py-1 text-xs bg-muted text-muted-foreground rounded">
                      已禁用
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>测试集合: {project.collection_count}</span>
                  <span>执行次数: {project.execution_count}</span>
                </div>
                {project.apifox_project_id && (
                  <div className="text-xs text-muted-foreground">
                    Apifox ID: {project.apifox_project_id}
                    {project.last_sync_at && (
                      <span className="ml-2">
                        最后同步:{" "}
                        {new Date(project.last_sync_at).toLocaleString("zh-CN")}
                      </span>
                    )}
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Link
                    to="/projects/$projectId"
                    params={{ projectId: project.id }}
                    className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-8 px-3"
                  >
                    进入
                  </Link>
                  {project.apifox_project_id && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleSync(project.id)}
                    >
                      同步
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => openEditDialog(project)}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(project.id)}
                  >
                    删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建项目</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">项目名称</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入项目名称"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">项目描述</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="输入项目描述（可选）"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="apifox-id">Apifox 项目 ID</Label>
              <Input
                id="apifox-id"
                value={formData.apifox_project_id}
                onChange={(e) =>
                  setFormData({ ...formData, apifox_project_id: e.target.value })
                }
                placeholder="输入 Apifox 项目 ID（可选）"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleCreate}>创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!editProject} onOpenChange={() => setEditProject(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑项目</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">项目名称</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="输入项目名称"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">项目描述</Label>
              <Input
                id="edit-description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="输入项目描述（可选）"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-apifox-id">Apifox 项目 ID</Label>
              <Input
                id="edit-apifox-id"
                value={formData.apifox_project_id}
                onChange={(e) =>
                  setFormData({ ...formData, apifox_project_id: e.target.value })
                }
                placeholder="输入 Apifox 项目 ID（可选）"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditProject(null)}>
              取消
            </Button>
            <Button onClick={handleUpdate}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>同步 Apifox 测试集合</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="sync-token">Apifox Access Token</Label>
              <Input
                id="sync-token"
                type="password"
                value={syncToken}
                onChange={(e) => setSyncToken(e.target.value)}
                placeholder="留空则使用系统配置的令牌"
              />
              <p className="text-xs text-muted-foreground">
                在 Apifox 网站生成：账号设置 → API 访问令牌
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={doSync} disabled={syncing}>
              {syncing ? "同步中..." : "开始同步"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export const Route = createFileRoute("/_layout/projects/")({
  component: ProjectsListPage,
})
