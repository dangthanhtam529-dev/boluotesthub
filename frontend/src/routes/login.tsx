import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  Link as RouterLink,
  redirect,
} from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import type { Body_login_login_access_token as AccessToken } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z.object({
  username: z.email({ message: "请输入有效的邮箱地址" }),
  password: z
    .string()
    .min(1, { message: "请输入密码" })
    .min(8, { message: "密码长度至少8位" }),
}) satisfies z.ZodType<AccessToken>

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "登录 - 测试管理平台",
      },
    ],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      username: "",
      password: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    loginMutation.mutate(data)
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-5"
        >
          {/* 标题 */}
          <div className="text-center">
            <h2 className="text-lg font-medium text-foreground">
              账号登录
            </h2>
            <p className="text-muted-foreground mt-1 text-xs">
              请输入您的账号信息
            </p>
          </div>

          {/* 表单 */}
          <div className="space-y-4">
            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm">邮箱</FormLabel>
                  <FormControl>
                    <Input
                      data-testid="email-input"
                      placeholder="请输入邮箱"
                      type="email"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel className="text-sm">密码</FormLabel>
                    <RouterLink
                      to="/recover-password"
                      className="text-xs text-muted-foreground hover:text-primary transition-colors"
                    >
                      忘记密码？
                    </RouterLink>
                  </div>
                  <FormControl>
                    <PasswordInput
                      data-testid="password-input"
                      placeholder="请输入密码"
                      className="h-10"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <LoadingButton
            type="submit"
            loading={loginMutation.isPending}
            className="w-full h-10"
            data-testid="login-button"
          >
            登录
          </LoadingButton>

          <p className="text-center text-xs text-muted-foreground">
            还没有账号？{" "}
            <RouterLink
              to="/signup"
              className="text-primary hover:underline"
            >
              注册
            </RouterLink>
          </p>
        </form>
      </Form>
    </AuthLayout>
  )
}
