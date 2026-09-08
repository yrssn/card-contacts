<template>
  <div class="login-bg">
    <el-card class="login-card">
      <h2>名片快查</h2>
      <p class="tip">拍一张，确认后录入金山文档通讯录</p>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" size="large" prefix-icon="User" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" placeholder="密码" size="large" prefix-icon="Lock" show-password @keyup.enter="submit" /></el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="submit">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const store = useUserStore()
const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username || !form.password) return
  loading.value = true
  try {
    await store.login(form.username, form.password)
    router.replace('/cards')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-bg { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1f2d3d, #3a506b); }
.login-card { width: 380px; padding: 12px; }
h2 { margin: 0 0 4px; text-align: center; }
.tip { text-align: center; margin: 0 0 20px; }
</style>
