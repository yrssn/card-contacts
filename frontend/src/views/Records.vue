<template>
  <div class="page">
    <div class="page-header">
      <h2>录入记录</h2>
      <div>
        <el-checkbox v-if="store.isAdmin" v-model="mine" @change="load">只看我的</el-checkbox>
        <el-button style="margin-left:12px" @click="load" :loading="loading">刷新</el-button>
      </div>
    </div>
    <el-table :data="rows" v-loading="loading" stripe>
      <el-table-column label="照片" width="130">
        <template #default="{ row }">
          <el-image v-if="row.front_image_url" :src="row.front_image_url" :preview-src-list="[row.front_image_url, row.back_image_url].filter(Boolean)" fit="cover" style="width:100px;height:60px;border-radius:4px" preview-teleported />
        </template>
      </el-table-column>
      <el-table-column label="姓名" prop="card.name" width="120" />
      <el-table-column label="公司" prop="card.company" min-width="160" />
      <el-table-column label="职位" prop="card.department" min-width="120" />
      <el-table-column label="电话" prop="card.phone" min-width="140" />
      <el-table-column label="邮箱" prop="card.email" min-width="160" />
      <el-table-column label="分类" prop="category_key" width="100" />
      <el-table-column label="导入人" prop="importer" width="100" />
      <el-table-column label="状态" width="150">
        <template #default="{ row }">
          <el-tooltip v-if="row.status === 'synced'" :content="row.warning || '文字与照片均已写入'">
            <el-tag :type="row.warning ? 'warning' : 'success'">已同步 行{{ row.kdocs_row }}{{ row.duplicate ? '（重复）' : '' }}{{ row.warning ? '（照片为链接）' : '' }}</el-tag>
          </el-tooltip>
          <el-tooltip v-else :content="row.error"><el-tag type="danger">同步失败</el-tag></el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="160">
        <template #default="{ row }">{{ new Date(row.created_at + 'Z').toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'synced'" size="small" type="primary" link @click="retry(row)">重试</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type CardRecord } from '@/api'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const rows = ref<CardRecord[]>([])
const loading = ref(false)
const mine = ref(false)

async function load() {
  loading.value = true
  try { rows.value = await api.records(mine.value) } finally { loading.value = false }
}
async function retry(row: CardRecord) {
  await api.retry(row.id)
  ElMessage.success('已重新同步')
  load()
}
onMounted(load)
</script>
