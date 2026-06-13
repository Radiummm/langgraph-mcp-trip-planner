<template>
  <div class="home-container">
    <section class="intake-shell">
      <aside class="intake-sidebar">
        <div class="sidebar-rule"></div>
        <p class="eyebrow">Travel Brief</p>
        <h1 class="page-title">建立一份行程档案</h1>
        <p class="page-subtitle">把目的地、日期、同行偏好和节奏约束放在一页里，后续结果会按天拆成路线、住宿、预算和地图。</p>
        <div class="brief-list">
          <div class="brief-item">
            <span>01</span>
            <strong>基础条件</strong>
            <small>城市、日期、天数</small>
          </div>
          <div class="brief-item">
            <span>02</span>
            <strong>旅行偏好</strong>
            <small>交通、住宿、主题</small>
          </div>
          <div class="brief-item">
            <span>03</span>
            <strong>特殊说明</strong>
            <small>节奏、同行人、忌口</small>
          </div>
        </div>
      </aside>

      <main class="intake-panel">
        <a-form :model="formData" layout="vertical" @finish="handleSubmit">
          <section class="form-block">
            <div class="block-head">
              <span>01</span>
              <h2>出行范围</h2>
            </div>
            <a-row :gutter="14">
              <a-col :xs="24" :md="8">
                <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                  <template #label><span class="form-label">目的地城市</span></template>
                  <a-input v-model:value="formData.city" placeholder="北京" size="large" class="field" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="6">
                <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                  <template #label><span class="form-label">开始日期</span></template>
                  <a-date-picker v-model:value="formData.start_date" style="width: 100%" size="large" class="field" placeholder="选择日期" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="6">
                <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                  <template #label><span class="form-label">结束日期</span></template>
                  <a-date-picker v-model:value="formData.end_date" style="width: 100%" size="large" class="field" placeholder="选择日期" />
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="4">
                <a-form-item>
                  <template #label><span class="form-label">天数</span></template>
                  <div class="days-counter">
                    <strong>{{ formData.travel_days }}</strong>
                    <span>天</span>
                  </div>
                </a-form-item>
              </a-col>
            </a-row>
          </section>

          <section class="form-block compact-block">
            <div class="block-head">
              <span>02</span>
              <h2>偏好与约束</h2>
            </div>
            <a-row :gutter="14">
              <a-col :xs="24" :md="8">
                <a-form-item name="transportation">
                  <template #label><span class="form-label">交通方式</span></template>
                  <a-select v-model:value="formData.transportation" size="large" class="field">
                    <a-select-option value="公共交通">公共交通</a-select-option>
                    <a-select-option value="自驾">自驾</a-select-option>
                    <a-select-option value="步行">步行</a-select-option>
                    <a-select-option value="混合">混合</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item name="accommodation">
                  <template #label><span class="form-label">住宿类型</span></template>
                  <a-select v-model:value="formData.accommodation" size="large" class="field">
                    <a-select-option value="经济型酒店">经济型酒店</a-select-option>
                    <a-select-option value="舒适型酒店">舒适型酒店</a-select-option>
                    <a-select-option value="豪华酒店">豪华酒店</a-select-option>
                    <a-select-option value="民宿">民宿</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :xs="24" :md="8">
                <a-form-item name="preferences">
                  <template #label><span class="form-label">主题偏好</span></template>
                  <a-checkbox-group v-model:value="formData.preferences" class="preference-grid">
                    <a-checkbox value="历史文化">历史文化</a-checkbox>
                    <a-checkbox value="自然风光">自然风光</a-checkbox>
                    <a-checkbox value="美食">美食</a-checkbox>
                    <a-checkbox value="购物">购物</a-checkbox>
                    <a-checkbox value="艺术">艺术</a-checkbox>
                    <a-checkbox value="休闲">休闲</a-checkbox>
                  </a-checkbox-group>
                </a-form-item>
              </a-col>
            </a-row>
          </section>

          <section class="form-block">
            <div class="block-head">
              <span>03</span>
              <h2>备注</h2>
            </div>
            <a-form-item name="free_text_input">
              <a-textarea v-model:value="formData.free_text_input" placeholder="例如：带老人同行；每天不要太赶；午餐尽量靠近景点；避开排队太久的项目。" :rows="4" size="large" class="field notes" />
            </a-form-item>
          </section>

          <div class="submit-strip">
            <div>
              <strong>将生成</strong>
              <span>每日路线、景点坐标、住宿建议、餐饮与预算</span>
            </div>
            <a-button type="primary" html-type="submit" :loading="loading" size="large" class="submit-button">
              <template v-if="!loading">生成行程</template>
              <template v-else>生成中</template>
            </a-button>
          </div>

          <div v-if="loading" class="loading-container">
            <a-progress :percent="loadingProgress" status="active" :stroke-color="'#8a5a2b'" :stroke-width="7" />
            <p>{{ loadingStatus }}</p>
          </div>
        </a-form>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { generateTripPlan } from '@/services/api'
import type { TripFormData } from '@/types'
import type { Dayjs } from 'dayjs'

type TripFormState = Omit<TripFormData, 'start_date' | 'end_date'> & {
  start_date: Dayjs | null
  end_date: Dayjs | null
}

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = reactive<TripFormState>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: ''
})

// 监听日期变化,自动计算旅行天数
watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择日期')
    return
  }

  loading.value = true
  loadingProgress.value = 0
  loadingStatus.value = '正在整理目的地信息...'

  // 模拟进度更新
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10

      // 更新状态文本
      if (loadingProgress.value <= 30) {
        loadingStatus.value = '正在检索景点与坐标...'
      } else if (loadingProgress.value <= 50) {
        loadingStatus.value = '正在补充天气与交通信息...'
      } else if (loadingProgress.value <= 70) {
        loadingStatus.value = '正在匹配住宿与餐饮...'
      } else {
        loadingStatus.value = '正在排布每日路线...'
      }
    }
  }, 500)

  try {
    const requestData: TripFormData = {
      city: formData.city,
      start_date: formData.start_date.format('YYYY-MM-DD'),
      end_date: formData.end_date.format('YYYY-MM-DD'),
      travel_days: formData.travel_days,
      transportation: formData.transportation,
      accommodation: formData.accommodation,
      preferences: formData.preferences,
      free_text_input: formData.free_text_input
    }

    const response = await generateTripPlan(requestData)

    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '生成完成'

    if (response.success && response.data) {
      // 保存到sessionStorage
      sessionStorage.setItem('tripPlan', JSON.stringify(response.data))

      message.success('旅行计划生成成功')

      // 短暂延迟后跳转
      setTimeout(() => {
        router.push('/result')
      }, 500)
    } else {
      message.error(response.message || '生成失败')
    }
  } catch (error: any) {
    clearInterval(progressInterval)
    message.error(error.message || '生成旅行计划失败,请稍后重试')
  } finally {
    setTimeout(() => {
      loading.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-container {
  min-height: calc(100vh - 56px);
  padding: 34px;
  background:
    linear-gradient(90deg, rgba(20, 31, 43, 0.04) 1px, transparent 1px),
    linear-gradient(180deg, rgba(20, 31, 43, 0.04) 1px, transparent 1px),
    #ece8df;
  background-size: 28px 28px;
}

.intake-shell {
  max-width: 1220px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 20px;
}

.intake-sidebar,
.intake-panel {
  border: 1px solid #d5cbbb;
  background: #fbfaf6;
  box-shadow: 0 14px 30px rgba(45, 36, 24, 0.08);
}

.intake-sidebar {
  position: relative;
  min-height: 640px;
  padding: 34px 30px;
  overflow: hidden;
}

.sidebar-rule {
  width: 58px;
  height: 5px;
  margin-bottom: 30px;
  background: #8a5a2b;
}

.eyebrow {
  margin: 0 0 12px;
  color: #78664f;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.page-title {
  margin: 0;
  color: #1f2933;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 42px;
  font-weight: 700;
  line-height: 1.08;
}

.page-subtitle {
  margin: 20px 0 0;
  color: #685d50;
  font-size: 15px;
  line-height: 1.9;
}

.brief-list {
  position: absolute;
  left: 30px;
  right: 30px;
  bottom: 30px;
  display: grid;
  gap: 12px;
}

.brief-item {
  display: grid;
  grid-template-columns: 34px 1fr;
  column-gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #ded4c4;
}

.brief-item span {
  color: #8a5a2b;
  font-size: 12px;
  font-weight: 800;
}

.brief-item strong {
  color: #263238;
  font-size: 14px;
}

.brief-item small {
  grid-column: 2;
  color: #817365;
  font-size: 12px;
}

.intake-panel {
  padding: 24px;
}

.form-block {
  padding: 22px 22px 14px;
  border: 1px solid #ded4c4;
  background: #ffffff;
}

.form-block + .form-block {
  margin-top: 14px;
}

.compact-block {
  background: #fdfbf6;
}

.block-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}

.block-head span {
  color: #8a5a2b;
  font-size: 12px;
  font-weight: 800;
}

.block-head h2 {
  margin: 0;
  color: #202933;
  font-size: 18px;
  font-weight: 750;
}

.form-label {
  color: #3d3a34;
  font-size: 13px;
  font-weight: 700;
}

.field :deep(.ant-input),
.field :deep(.ant-picker),
.field :deep(.ant-select-selector),
.notes :deep(.ant-input) {
  border-radius: 0 !important;
  border-color: #cbbfae !important;
  box-shadow: none !important;
}

.field :deep(.ant-input:hover),
.field :deep(.ant-picker:hover),
.field:hover :deep(.ant-select-selector),
.notes :deep(.ant-input:hover) {
  border-color: #8a5a2b !important;
}

.days-counter {
  display: flex;
  align-items: baseline;
  justify-content: center;
  height: 40px;
  border: 1px solid #b99c77;
  background: #f3eadc;
  color: #5f3a17;
}

.days-counter strong {
  margin-right: 4px;
  font-size: 22px;
}

.preference-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.preference-grid :deep(.ant-checkbox-wrapper) {
  margin: 0;
  padding: 7px 8px;
  border: 1px solid #d6cabb;
  background: #ffffff;
  font-size: 13px;
}

.submit-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-top: 16px;
  padding: 16px 18px;
  border: 1px solid #d5cbbb;
  background: #242a31;
  color: #ffffff;
}

.submit-strip div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.submit-strip span {
  color: #c9c2b8;
  font-size: 13px;
}

.submit-button {
  min-width: 142px;
  border-radius: 0;
  background: #8a5a2b;
  border-color: #8a5a2b;
  box-shadow: none;
  font-weight: 750;
}

.submit-button:hover {
  background: #6f451d !important;
  border-color: #6f451d !important;
}

.loading-container {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid #ded4c4;
  background: #fffdf8;
}

.loading-container p {
  margin: 8px 0 0;
  color: #685d50;
  font-size: 13px;
}

@media (max-width: 900px) {
  .home-container {
    padding: 18px;
  }

  .intake-shell {
    grid-template-columns: 1fr;
  }

  .intake-sidebar {
    min-height: auto;
  }

  .brief-list {
    position: static;
    margin-top: 32px;
  }

  .submit-strip {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
