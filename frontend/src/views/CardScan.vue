<template>
  <div class="page">
    <el-steps :active="step" finish-status="success" simple class="steps">
      <el-step title="拍摄 / 上传" />
      <el-step title="识别" />
      <el-step title="确认入库" />
    </el-steps>

    <el-row :gutter="20">
      <el-col :xs="24" :md="11">
        <el-card>
          <template #header>
            <div class="card-title">
              <span>名片照片</span>
              <el-radio-group v-model="mode" size="small">
                <el-radio-button value="single">单面</el-radio-button>
                <el-radio-button value="double">正反两面</el-radio-button>
              </el-radio-group>
            </div>
          </template>

          <div class="uploaders">
            <div class="uploader">
              <div class="label">正面 <span class="required">*</span></div>
              <label class="drop">
                <input type="file" accept="image/*" hidden @change="onPick($event, 'front')" />
                <img v-if="frontPreview" :src="frontPreview" />
                <div v-else class="placeholder"><el-icon :size="36"><Camera /></el-icon><span>点击拍照或选择图片</span></div>
              </label>
            </div>
            <div v-if="mode === 'double'" class="uploader">
              <div class="label">反面</div>
              <label class="drop">
                <input type="file" accept="image/*" hidden @change="onPick($event, 'back')" />
                <img v-if="backPreview" :src="backPreview" />
                <div v-else class="placeholder"><el-icon :size="36"><Camera /></el-icon><span>点击拍照或选择图片</span></div>
              </label>
            </div>
          </div>

          <div style="margin-top:16px; display:flex; gap:10px">
            <el-button type="primary" :disabled="!frontFile" :loading="recognizing" @click="recognize">
              {{ recognizing ? '识别中…' : '开始识别' }}
            </el-button>
            <el-button @click="reset">重新开始</el-button>
          </div>
          <p class="tip" style="margin-top:10px">保持光线充足、文字清晰、尽量避免反光。支持中、日、英名片。</p>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="13">
        <el-card>
          <template #header>
            <div class="card-title">
              <span>联系人信息</span>
              <span v-if="result" class="tip">识别模型：{{ result.model_used }}</span>
            </div>
          </template>

          <el-form label-width="110px" size="default">
            <el-form-item label="录入分类" required>
              <el-radio-group v-model="categoryKey">
                <el-radio-button v-for="c in categories" :key="c.key" :value="c.key">{{ c.label }}</el-radio-button>
              </el-radio-group>
              <div class="tip" v-if="currentCategory">将写入金山表格工作表「{{ currentCategory.sheet_name }}」</div>
            </el-form-item>
            <el-divider />
            <el-row :gutter="12">
              <el-col :xs="24" :sm="12"><el-form-item label="姓名"><el-input v-model="card.name" /></el-form-item></el-col>
              <el-col :xs="12" :sm="6"><el-form-item label="语种" label-width="60px">
                <el-select v-model="card.language"><el-option value="JP" /><el-option value="CN" /><el-option value="EN" /></el-select>
              </el-form-item></el-col>
              <el-col :xs="12" :sm="6"><el-form-item label="性别" label-width="60px">
                <el-select v-model="card.sex" clearable><el-option value="男" /><el-option value="女" /></el-select>
              </el-form-item></el-col>
            </el-row>
            <el-form-item label="公司名">
              <div style="display:flex; gap:8px; width:100%">
                <el-input v-model="card.company" />
                <el-button :loading="enriching" :disabled="!card.company" @click="enrich">重新检索</el-button>
              </div>
            </el-form-item>
            <el-alert v-if="summary" type="success" :closable="false" title="公司概述（联网检索）" style="margin-bottom:14px">
              <div style="white-space:pre-wrap">{{ summary }}</div>
              <div v-if="sources.length" class="tip" style="margin-top:6px">来源：<a v-for="s in sources" :key="s.url" :href="s.url" target="_blank" style="margin-right:8px">{{ s.title || s.url }}</a></div>
            </el-alert>
            <el-alert v-else-if="searchError" type="warning" :closable="false" :title="`联网检索未成功：${searchError}`" style="margin-bottom:14px" />
            <el-form-item label="职位"><el-input v-model="card.department" placeholder="部门 + 职位" /></el-form-item>
            <el-row :gutter="12">
              <el-col :xs="24" :sm="12"><el-form-item label="主营业务关键词"><el-input v-model="card.businessKeywords" maxlength="10" show-word-limit /></el-form-item></el-col>
              <el-col :xs="24" :sm="12"><el-form-item label="产品/服务类型"><el-input v-model="card.productServiceType" maxlength="10" show-word-limit /></el-form-item></el-col>
            </el-row>
            <el-form-item label="电话"><el-input v-model="card.phone" placeholder="多个用 / 分隔" /></el-form-item>
            <el-form-item label="邮箱"><el-input v-model="card.email" placeholder="多个用 / 分隔" /></el-form-item>
            <el-form-item label="官网"><el-input v-model="card.website" /></el-form-item>
            <el-form-item label="备注"><el-input v-model="card.note" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="导入人"><el-input :model-value="store.user?.display_name || store.user?.username" disabled /></el-form-item>
          </el-form>

          <div class="confirm-bar">
            <el-button type="success" class="confirm-btn" :disabled="!result || !categoryKey" :loading="confirming" @click="confirm">确认并录入金山文档</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="doneVisible" title="录入成功" width="420px">
      <el-result icon="success" :title="done?.duplicate ? '已存在，已补充照片/导入人' : '已写入金山文档'"
        :sub-title="`工作表「${currentCategory?.sheet_name}」第 ${done?.kdocs_row} 行`" />
      <el-alert v-if="done?.warning" type="warning" :closable="false" title="文字已录入，照片以链接形式写入"
        :description="`${done.warning}`" />
      <template #footer>
        <el-button type="primary" @click="doneVisible = false; reset()">继续下一张</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api, type Card, type CardRecord, type Category, type RecognizeOut } from '@/api'
import { useUserStore } from '@/stores/user'

const store = useUserStore()
const mode = ref<'single' | 'double'>('single')
const step = ref(0)
const frontFile = ref<File | null>(null)
const backFile = ref<File | null>(null)
const frontPreview = ref('')
const backPreview = ref('')
const recognizing = ref(false)
const confirming = ref(false)
const result = ref<RecognizeOut | null>(null)
const categories = ref<Category[]>([])
const categoryKey = ref('')
const doneVisible = ref(false)
const done = ref<CardRecord | null>(null)
const enriching = ref(false)
const summary = ref('')
const searchError = ref('')
const sources = ref<{ title: string; url: string }[]>([])

const emptyCard = (): Card => ({
  language: '', name: '', sex: '', note: '', department: '', businessKeywords: '',
  productServiceType: '', company: '', website: '', email: '', phone: '',
})
const card = reactive<Card>(emptyCard())
const currentCategory = computed(() => categories.value.find((c) => c.key === categoryKey.value))

onMounted(async () => {
  categories.value = await api.categories()
})

function onPick(e: Event, side: 'front' | 'back') {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const url = URL.createObjectURL(file)
  if (side === 'front') { frontFile.value = file; frontPreview.value = url } else { backFile.value = file; backPreview.value = url }
  step.value = 0
}

async function recognize() {
  if (!frontFile.value) return
  recognizing.value = true
  try {
    result.value = await api.recognize(frontFile.value, mode.value === 'double' ? backFile.value : null)
    Object.assign(card, result.value.card)
    summary.value = result.value.company_summary || ''
    searchError.value = result.value.search_error || ''
    sources.value = result.value.sources || []
    step.value = 2
    ElMessage.success('识别完成，请核对后确认')
  } finally {
    recognizing.value = false
  }
}

async function enrich() {
  if (!card.company) return
  enriching.value = true
  try {
    const info = await api.enrichCompany({ company: card.company, website: card.website, language: card.language })
    if (info.businessKeywords) card.businessKeywords = info.businessKeywords
    if (info.productServiceType) card.productServiceType = info.productServiceType
    if (info.website && !card.website) card.website = info.website
    summary.value = info.summary
    sources.value = info.sources || []
    searchError.value = ''
    ElMessage.success('已根据网络资料更新主营业务字段')
  } finally {
    enriching.value = false
  }
}

async function confirm() {
  if (!result.value || !categoryKey.value) return
  confirming.value = true
  try {
    done.value = await api.confirm({
      category_key: categoryKey.value,
      card: { ...card },
      front_image: result.value.front_image,
      back_image: mode.value === 'double' ? result.value.back_image : '',
    })
    step.value = 3
    doneVisible.value = true
  } finally {
    confirming.value = false
  }
}

function reset() {
  frontFile.value = backFile.value = null
  frontPreview.value = backPreview.value = ''
  result.value = null
  Object.assign(card, emptyCard())
  summary.value = searchError.value = ''
  sources.value = []
  step.value = 0
}
</script>

<style scoped>
.card-title { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
.steps { margin-bottom: 20px; }
.confirm-bar { display: flex; justify-content: flex-end; gap: 10px; }
@media (max-width: 767px) {
  .steps { display: none; }
  .uploaders { flex-direction: column; }
  .confirm-btn { width: 100%; }
}
.uploaders { display: flex; gap: 12px; }
.uploader { flex: 1; }
.label { font-size: 13px; margin-bottom: 6px; color: #606266; }
.required { color: #f56c6c; }
.drop { display: block; border: 2px dashed #dcdfe6; border-radius: 8px; aspect-ratio: 16/10; cursor: pointer; overflow: hidden; background: #fafafa; }
.drop:hover { border-color: #409eff; }
.drop img { width: 100%; height: 100%; object-fit: contain; }
.placeholder { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #909399; font-size: 13px; }
</style>
