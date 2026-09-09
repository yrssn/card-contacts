<template>
  <el-container class="layout">
    <el-aside v-if="!isMobile" width="200px" class="aside">
      <div class="logo">名片快查</div>
      <el-menu :default-active="route.path" router background-color="#1f2d3d" text-color="#cfd6e0" active-text-color="#fff">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path"><el-icon><component :is="m.icon" /></el-icon>{{ m.title }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-drawer v-else v-model="drawer" direction="ltr" size="220px" :with-header="false" class="nav-drawer">
      <div class="logo">名片快查</div>
      <el-menu :default-active="route.path" router background-color="#1f2d3d" text-color="#cfd6e0" active-text-color="#fff" @select="drawer = false">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path"><el-icon><component :is="m.icon" /></el-icon>{{ m.title }}</el-menu-item>
      </el-menu>
    </el-drawer>
    <el-container>
      <el-header class="header">
        <span class="title">
          <el-button v-if="isMobile" text :icon="Menu" @click="drawer = true" />
          {{ route.meta.title }}
        </span>
        <el-dropdown @command="onCommand">
          <span class="user">{{ store.user?.display_name || store.user?.username }}
            <el-tag v-if="!isMobile" size="small" :type="store.isAdmin ? 'danger' : 'info'" style="margin-left:6px">{{ store.isAdmin ? '管理员' : '用户' }}</el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>

    <el-dialog v-model="pwdVisible" title="修改密码" width="400px" >
      <el-form label-width="80px">
        <el-form-item label="原密码"><el-input v-model="pwd.old" type="password" show-password /></el-form-item>
        <el-form-item label="新密码"><el-input v-model="pwd.new1" type="password" show-password /></el-form-item>
        <el-form-item label="确认"><el-input v-model="pwd.new2" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" @click="changePwd">保存</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Camera, Collection, Cpu, Document, Menu, Tickets, User } from '@element-plus/icons-vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'
import { useIsMobile } from '@/composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const isMobile = useIsMobile()
const drawer = ref(false)
const pwdVisible = ref(false)

const menus = computed(() => [
  { path: '/cards', title: '名片识别', icon: Camera },
  { path: '/records', title: '录入记录', icon: Tickets },
  ...(store.isAdmin
    ? [
        { path: '/categories', title: '名片分类', icon: Collection },
        { path: '/models', title: '视觉模型', icon: Cpu },
        { path: '/kdocs', title: '金山文档', icon: Document },
        { path: '/users', title: '用户管理', icon: User },
      ]
    : []),
])
const pwd = reactive({ old: '', new1: '', new2: '' })

function onCommand(cmd: string) {
  if (cmd === 'logout') {
    store.logout()
    router.replace('/login')
  } else if (cmd === 'password') {
    pwd.old = pwd.new1 = pwd.new2 = ''
    pwdVisible.value = true
  }
}

async function changePwd() {
  if (pwd.new1.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (pwd.new1 !== pwd.new2) return ElMessage.warning('两次密码不一致')
  await api.changePassword(pwd.old, pwd.new1)
  ElMessage.success('密码已修改')
  pwdVisible.value = false
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #1f2d3d; }
.title { display: inline-flex; align-items: center; gap: 4px; }
.logo { color: #fff; font-size: 18px; font-weight: 600; padding: 18px 20px; letter-spacing: 2px; }
.el-menu { border-right: none; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #ebeef5; font-size: 16px; }
.user { cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
</style>

<style>
.nav-drawer { background: #1f2d3d; }
.nav-drawer .el-drawer__body { padding: 0; }
</style>
