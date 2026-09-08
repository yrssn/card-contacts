<template>
  <el-container class="layout">
    <el-aside width="200px" class="aside">
      <div class="logo">名片快查</div>
      <el-menu :default-active="route.path" router background-color="#1f2d3d" text-color="#cfd6e0" active-text-color="#fff">
        <el-menu-item index="/cards"><el-icon><Camera /></el-icon>名片识别</el-menu-item>
        <el-menu-item index="/records"><el-icon><Tickets /></el-icon>录入记录</el-menu-item>
        <template v-if="store.isAdmin">
          <el-menu-item index="/categories"><el-icon><Collection /></el-icon>名片分类</el-menu-item>
          <el-menu-item index="/models"><el-icon><Cpu /></el-icon>视觉模型</el-menu-item>
          <el-menu-item index="/kdocs"><el-icon><Document /></el-icon>金山文档</el-menu-item>
          <el-menu-item index="/users"><el-icon><User /></el-icon>用户管理</el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span>{{ route.meta.title }}</span>
        <el-dropdown @command="onCommand">
          <span class="user">{{ store.user?.display_name || store.user?.username }}
            <el-tag size="small" :type="store.isAdmin ? 'danger' : 'info'" style="margin-left:6px">{{ store.isAdmin ? '管理员' : '用户' }}</el-tag>
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

    <el-dialog v-model="pwdVisible" title="修改密码" width="400px">
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
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const pwdVisible = ref(false)
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
.logo { color: #fff; font-size: 18px; font-weight: 600; padding: 18px 20px; letter-spacing: 2px; }
.el-menu { border-right: none; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #ebeef5; font-size: 16px; }
.user { cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
</style>
