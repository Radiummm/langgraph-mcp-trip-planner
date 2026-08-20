<template>
  <div class="result-container">
    <header class="page-header">
      <button class="text-button" type="button" @click="goBack">← 重新规划</button>
      <div class="page-actions">
        <a-button v-if="!editMode" @click="toggleEditMode">调整行程</a-button>
        <template v-else>
          <a-button type="primary" @click="saveChanges">保存修改</a-button>
          <a-button @click="cancelEdit">取消</a-button>
        </template>
        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="exportAsImage">导出图片</a-menu-item>
              <a-menu-item key="pdf" @click="exportAsPDF">导出 PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button>保存副本 <DownOutlined /></a-button>
        </a-dropdown>
      </div>
    </header>

    <div v-if="tripPlan" class="content-wrapper">
      <aside class="side-nav">
        <a-affix :offset-top="76">
          <div class="nav-sheet">
            <p>本次行程</p>
            <a-menu mode="inline" :selected-keys="[activeSection]" @click="scrollToSection">
              <a-menu-item key="overview">概要</a-menu-item>
              <a-menu-item v-if="tripPlan.budget" key="budget">费用</a-menu-item>
              <a-menu-item key="map">路线地图</a-menu-item>
              <a-sub-menu key="days" title="每日安排">
                <a-menu-item v-for="(day, index) in tripPlan.days" :key="`day-${index}`">
                  Day {{ day.day_index + 1 }}
                </a-menu-item>
              </a-sub-menu>
              <a-menu-item v-if="tripPlan.weather_info?.length" key="weather">天气</a-menu-item>
            </a-menu>
          </div>
        </a-affix>
      </aside>

      <main class="main-content">
        <section id="overview" class="trip-hero">
          <div>
            <p class="section-kicker">TRAVEL NOTES · {{ tripPlan.days.length }} DAYS</p>
            <h1>{{ tripPlan.city }}</h1>
            <p class="trip-date">{{ tripPlan.start_date }} — {{ tripPlan.end_date }}</p>
          </div>
          <div class="editor-note">
            <span>行前建议</span>
            <p>{{ tripPlan.overall_suggestions }}</p>
          </div>
        </section>

        <section class="top-info-section">
          <div v-if="tripPlan.budget" id="budget" class="budget-sheet">
            <div class="section-heading">
              <span>01</span>
              <div><p>ESTIMATE</p><h2>费用概算</h2></div>
            </div>
            <div class="budget-list">
              <div><span>门票</span><strong>¥{{ tripPlan.budget.total_attractions }}</strong></div>
              <div><span>住宿</span><strong>¥{{ tripPlan.budget.total_hotels }}</strong></div>
              <div><span>餐饮</span><strong>¥{{ tripPlan.budget.total_meals }}</strong></div>
              <div><span>交通</span><strong>¥{{ tripPlan.budget.total_transportation }}</strong></div>
            </div>
            <div class="budget-total">
              <span>预计合计</span>
              <strong>¥{{ tripPlan.budget.total }}</strong>
            </div>
          </div>

          <div id="map" class="map-sheet">
            <div class="section-heading light">
              <span>02</span>
              <div><p>ROUTE</p><h2>路线地图</h2></div>
            </div>
            <div id="amap-container" class="map-container"></div>
          </div>
        </section>

        <section class="days-section">
          <div class="section-heading days-heading">
            <span>03</span>
            <div><p>DAY BY DAY</p><h2>每日安排</h2></div>
          </div>
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel v-for="(day, index) in tripPlan.days" :key="index" :id="`day-${index}`">
              <template #header>
                <div class="day-header">
                  <span class="day-number">DAY {{ String(day.day_index + 1).padStart(2, '0') }}</span>
                  <strong>{{ day.description }}</strong>
                  <time>{{ day.date }}</time>
                </div>
              </template>

              <div class="day-meta">
                <div><span>移动方式</span><strong>{{ day.transportation }}</strong></div>
                <div><span>落脚处</span><strong>{{ day.accommodation }}</strong></div>
                <div><span>当日安排</span><strong>{{ day.attractions.length }} 处景点</strong></div>
              </div>

              <div class="route-grid">
                <article v-for="(item, attrIndex) in day.attractions" :key="`${item.name}-${attrIndex}`" class="place-entry">
                  <div class="attraction-image-wrapper">
                    <img :src="getAttractionImage(item.name, attrIndex)" :alt="item.name" class="attraction-image" @error="handleImageError" />
                    <span class="attraction-badge">{{ String(attrIndex + 1).padStart(2, '0') }}</span>
                    <span v-if="item.ticket_price" class="price-tag">门票 ¥{{ item.ticket_price }}</span>
                  </div>
                  <div class="place-copy">
                    <div class="place-title-row">
                      <h3>{{ item.name }}</h3>
                      <div v-if="editMode" class="edit-actions">
                        <a-button size="small" :disabled="attrIndex === 0" @click="moveAttraction(day.day_index, attrIndex, 'up')">上移</a-button>
                        <a-button size="small" :disabled="attrIndex === day.attractions.length - 1" @click="moveAttraction(day.day_index, attrIndex, 'down')">下移</a-button>
                        <a-button size="small" danger @click="deleteAttraction(day.day_index, attrIndex)">删除</a-button>
                      </div>
                    </div>
                    <template v-if="editMode">
                      <label>地址<a-input v-model:value="item.address" /></label>
                      <label>游览时长（分钟）<a-input-number v-model:value="item.visit_duration" :min="10" :max="480" /></label>
                      <label>说明<a-textarea v-model:value="item.description" :rows="3" /></label>
                    </template>
                    <template v-else>
                      <p class="place-meta">{{ item.address }} · {{ item.visit_duration }} 分钟<span v-if="item.rating"> · {{ item.rating }} 分</span></p>
                      <p class="place-description">{{ item.description }}</p>
                    </template>
                  </div>
                </article>
              </div>

              <div class="day-details">
                <div v-if="day.hotel" class="stay-note">
                  <p class="detail-label">今晚住这里</p>
                  <h3>{{ day.hotel.name }}</h3>
                  <p>{{ day.hotel.type }} · {{ day.hotel.price_range }} · 评分 {{ day.hotel.rating }}</p>
                  <small>{{ day.hotel.address }} · {{ day.hotel.distance }}</small>
                </div>
                <div class="meal-note">
                  <p class="detail-label">沿途吃什么</p>
                  <div v-for="meal in day.meals" :key="meal.type" class="meal-row">
                    <span>{{ getMealLabel(meal.type) }}</span>
                    <p><strong>{{ meal.name }}</strong><small v-if="meal.description">{{ meal.description }}</small></p>
                  </div>
                </div>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </section>

        <section v-if="tripPlan.weather_info?.length" id="weather" class="weather-section">
          <div class="section-heading">
            <span>04</span>
            <div><p>FORECAST</p><h2>天气参考</h2></div>
          </div>
          <div class="weather-list">
            <article v-for="item in tripPlan.weather_info" :key="item.date">
              <time>{{ item.date }}</time>
              <strong>{{ item.day_weather }} / {{ item.night_weather }}</strong>
              <span>{{ item.day_temp }}° — {{ item.night_temp }}°</span>
              <small>{{ item.wind_direction }} {{ item.wind_power }}</small>
            </article>
          </div>
        </section>
      </main>
    </div>

    <div v-else class="empty-state">
      <p>还没有可展示的行程</p>
      <a-button type="primary" @click="goBack">去创建行程</a-button>
    </div>

    <a-back-top :visibility-height="300"><div class="back-top-button">↑</div></a-back-top>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import type { TripPlan } from '@/types'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0]) // 默认展开第一天
let map: any = null

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    // 加载景点图片
    await loadAttractionPhotos()
    // 等待DOM渲染完成后初始化地图
    await nextTick()
    initMap()
  }
})

const goBack = () => {
  router.push('/')
}

// 滚动到指定区域
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 切换编辑模式
const toggleEditMode = () => {
  editMode.value = true
  // 保存原始数据用于取消编辑
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('进入编辑模式')
}

// 保存修改
const saveChanges = () => {
  editMode.value = false
  // 更新sessionStorage
  if (tripPlan.value) {
    sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  }
  message.success('修改已保存')

  // 重新初始化地图以反映更改
  if (map) {
    map.destroy()
  }
  nextTick(() => {
    initMap()
  })
}

// 取消编辑
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  }
  editMode.value = false
  message.info('已取消编辑')
}

// 删除景点
const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) {
    message.warning('每天至少需要保留一个景点')
    return
  }

  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
}

// 移动景点顺序
const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return

  const day = tripPlan.value.days[dayIndex]
  const attractions = day.attractions

  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = {
    breakfast: '早餐',
    lunch: '午餐',
    dinner: '晚餐',
    snack: '小吃'
  }
  return labels[type] || type
}

// 加载所有景点图片
const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return

  const promises: Promise<void>[] = []

  tripPlan.value.days.forEach(day => {
    day.attractions.forEach(attraction => {
      const promise = fetch(`/api/poi/photo?name=${encodeURIComponent(attraction.name)}`)
        .then(res => res.json())
        .then(data => {
          if (data.success && data.data.photo_url) {
            attractionPhotos.value[attraction.name] = data.data.photo_url
          }
        })
        .catch(err => {
          console.error(`获取${attraction.name}图片失败:`, err)
        })

      promises.push(promise)
    })
  })

  await Promise.all(promises)
}

// 获取景点图片
const getAttractionImage = (name: string, index: number): string => {
  // 如果已加载真实图片,返回真实图片
  if (attractionPhotos.value[name]) {
    return attractionPhotos.value[name]
  }

  // 无图片时使用与页面一致的纸张纹理占位，避免抢过行程内容
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
    <rect width="400" height="300" fill="#ded5c8"/>
    <path d="M0 75H400M0 150H400M0 225H400M100 0V300M200 0V300M300 0V300" stroke="#cfc3b2" stroke-width="1"/>
    <text x="200" y="142" text-anchor="middle" font-family="sans-serif" font-size="20" font-weight="600" fill="#51483e">${name}</text>
    <text x="200" y="174" text-anchor="middle" font-family="sans-serif" font-size="11" letter-spacing="2" fill="#8a5a2b">TRAVEL NOTE ${String(index + 1).padStart(2, '0')}</text>
  </svg>`

  return `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svg)))}`
}

// 图片加载失败时的处理
const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  // 使用灰色占位图
  img.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="400" height="300"%3E%3Crect width="400" height="300" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="18" fill="%23999"%3E图片加载失败%3C/text%3E%3C/svg%3E'
}



// 导出为图片
const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建一个独立的容器
    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'

    // 复制所有内容
    exportContainer.innerHTML = element.innerHTML

    // 处理地图截图
    const mapContainer = document.getElementById('amap-container')
    if (mapContainer && map) {
      const mapCanvas = mapContainer.querySelector('canvas')
      if (mapCanvas) {
        const mapSnapshot = mapCanvas.toDataURL('image/png')
        const exportMapContainer = exportContainer.querySelector('#amap-container')
        if (exportMapContainer) {
          exportMapContainer.innerHTML = `<img src="${mapSnapshot}" style="width:100%;height:100%;object-fit:cover;" />`
        }
      }
    }

    // 移除所有ant-card类,替换为纯div
    const cards = exportContainer.querySelectorAll('.ant-card')
    cards.forEach((card) => {
      const cardEl = card as HTMLElement
      try {
        cardEl.className = '' // 移除所有类
        cardEl.style.setProperty('background-color', '#ffffff')
        cardEl.style.setProperty('border-radius', '12px')
        cardEl.style.setProperty('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.1)')
        cardEl.style.setProperty('margin-bottom', '20px')
        cardEl.style.setProperty('overflow', 'hidden')
      } catch (err) {
        console.error('设置卡片样式失败:', err)
      }
    })

    // 处理卡片头部
    const cardHeads = exportContainer.querySelectorAll('.ant-card-head')
    cardHeads.forEach((head) => {
      const headEl = head as HTMLElement
      try {
        headEl.style.setProperty('background-color', '#20262c')
        headEl.style.setProperty('color', '#ffffff')
        headEl.style.setProperty('padding', '16px 24px')
        headEl.style.setProperty('font-size', '18px')
        headEl.style.setProperty('font-weight', '600')
      } catch (err) {
        console.error('设置卡片头部样式失败:', err)
      }
    })

    // 处理卡片内容
    const cardBodies = exportContainer.querySelectorAll('.ant-card-body')
    cardBodies.forEach((body) => {
      const bodyEl = body as HTMLElement
      bodyEl.style.setProperty('background-color', '#ffffff')
      bodyEl.style.setProperty('padding', '24px')
    })

    // 处理酒店卡片头部
    const hotelCards = exportContainer.querySelectorAll('.hotel-card')
    hotelCards.forEach((card) => {
      const head = card.querySelector('.ant-card-head') as HTMLElement
      if (head) {
        head.style.setProperty('background-color', '#1976d2')
      }
      (card as HTMLElement).style.setProperty('background-color', '#e3f2fd')
    })

    // 处理天气卡片
    const weatherCards = exportContainer.querySelectorAll('.weather-card')
    weatherCards.forEach((card) => {
      (card as HTMLElement).style.setProperty('background-color', '#e0f7fa')
    })

    // 处理预算总计
    const budgetTotal = exportContainer.querySelector('.budget-total')
    if (budgetTotal) {
      const el = budgetTotal as HTMLElement
      el.style.setProperty('background-color', '#20262c')
      el.style.setProperty('color', '#ffffff')
      el.style.setProperty('padding', '20px')
      el.style.setProperty('border-radius', '12px')
      el.style.setProperty('margin-bottom', '20px')
    }

    // 处理预算项
    const budgetItems = exportContainer.querySelectorAll('.budget-item')
    budgetItems.forEach((item) => {
      const el = item as HTMLElement
      el.style.setProperty('background-color', '#f5f7fa')
      el.style.setProperty('padding', '16px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '12px')
    })

    // 添加到body(隐藏)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    // 移除容器
    document.body.removeChild(exportContainer)

    // 转换为图片并下载
    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()

    message.success({ content: '图片导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出图片失败:', error)
    message.error({ content: `导出图片失败: ${error.message}`, key: 'export' })
  }
}

// 导出为PDF
const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })

    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) {
      throw new Error('未找到内容元素')
    }

    // 创建一个独立的容器
    const exportContainer = document.createElement('div')
    exportContainer.style.width = element.offsetWidth + 'px'
    exportContainer.style.backgroundColor = '#f5f7fa'
    exportContainer.style.padding = '20px'

    // 复制所有内容
    exportContainer.innerHTML = element.innerHTML

    // 处理地图截图
    const mapContainer = document.getElementById('amap-container')
    if (mapContainer && map) {
      const mapCanvas = mapContainer.querySelector('canvas')
      if (mapCanvas) {
        const mapSnapshot = mapCanvas.toDataURL('image/png')
        const exportMapContainer = exportContainer.querySelector('#amap-container')
        if (exportMapContainer) {
          exportMapContainer.innerHTML = `<img src="${mapSnapshot}" style="width:100%;height:100%;object-fit:cover;" />`
        }
      }
    }

    // 移除所有ant-card类,替换为纯div
    const cards = exportContainer.querySelectorAll('.ant-card')
    cards.forEach((card) => {
      const cardEl = card as HTMLElement
      try {
        cardEl.className = ''
        cardEl.style.setProperty('background-color', '#ffffff')
        cardEl.style.setProperty('border-radius', '12px')
        cardEl.style.setProperty('box-shadow', '0 4px 12px rgba(0, 0, 0, 0.1)')
        cardEl.style.setProperty('margin-bottom', '20px')
        cardEl.style.setProperty('overflow', 'hidden')
      } catch (err) {
        console.error('设置卡片样式失败:', err)
      }
    })

    // 处理卡片头部
    const cardHeads = exportContainer.querySelectorAll('.ant-card-head')
    cardHeads.forEach((head) => {
      const headEl = head as HTMLElement
      try {
        headEl.style.setProperty('background-color', '#20262c')
        headEl.style.setProperty('color', '#ffffff')
        headEl.style.setProperty('padding', '16px 24px')
        headEl.style.setProperty('font-size', '18px')
        headEl.style.setProperty('font-weight', '600')
      } catch (err) {
        console.error('设置卡片头部样式失败:', err)
      }
    })

    // 处理卡片内容
    const cardBodies = exportContainer.querySelectorAll('.ant-card-body')
    cardBodies.forEach((body) => {
      const bodyEl = body as HTMLElement
      bodyEl.style.setProperty('background-color', '#ffffff')
      bodyEl.style.setProperty('padding', '24px')
    })

    // 处理酒店卡片头部
    const hotelCards = exportContainer.querySelectorAll('.hotel-card')
    hotelCards.forEach((card) => {
      const head = card.querySelector('.ant-card-head') as HTMLElement
      if (head) {
        head.style.setProperty('background-color', '#1976d2')
      }
      (card as HTMLElement).style.setProperty('background-color', '#e3f2fd')
    })

    // 处理天气卡片
    const weatherCards = exportContainer.querySelectorAll('.weather-card')
    weatherCards.forEach((card) => {
      (card as HTMLElement).style.setProperty('background-color', '#e0f7fa')
    })

    // 处理预算总计
    const budgetTotal = exportContainer.querySelector('.budget-total')
    if (budgetTotal) {
      const el = budgetTotal as HTMLElement
      el.style.setProperty('background-color', '#20262c')
      el.style.setProperty('color', '#ffffff')
      el.style.setProperty('padding', '20px')
      el.style.setProperty('border-radius', '12px')
      el.style.setProperty('margin-bottom', '20px')
    }

    // 处理预算项
    const budgetItems = exportContainer.querySelectorAll('.budget-item')
    budgetItems.forEach((item) => {
      const el = item as HTMLElement
      el.style.setProperty('background-color', '#f5f7fa')
      el.style.setProperty('padding', '16px')
      el.style.setProperty('border-radius', '8px')
      el.style.setProperty('margin-bottom', '12px')
    })

    // 添加到body(隐藏)
    exportContainer.style.position = 'absolute'
    exportContainer.style.left = '-9999px'
    document.body.appendChild(exportContainer)

    const canvas = await html2canvas(exportContainer, {
      backgroundColor: '#f5f7fa',
      scale: 2,
      logging: false,
      useCORS: true,
      allowTaint: true
    })

    // 移除容器
    document.body.removeChild(exportContainer)

    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4'
    })

    const imgWidth = 210 // A4宽度(mm)
    const imgHeight = (canvas.height * imgWidth) / canvas.width

    // 如果内容高度超过一页,分页处理
    let heightLeft = imgHeight
    let position = 0

    pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
    heightLeft -= 297 // A4高度

    while (heightLeft > 0) {
      position = heightLeft - imgHeight
      pdf.addPage()
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight)
      heightLeft -= 297
    }

    pdf.save(`旅行计划_${tripPlan.value?.city}_${new Date().getTime()}.pdf`)

    message.success({ content: 'PDF导出成功!', key: 'export' })
  } catch (error: any) {
    console.error('导出PDF失败:', error)
    message.error({ content: `导出PDF失败: ${error.message}`, key: 'export' })
  }
}

const collectAttractions = () => {
  const attractions: any[] = []
  if (!tripPlan.value) return attractions

  tripPlan.value.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attraction, attrIndex) => {
      if (attraction.location && attraction.location.longitude && attraction.location.latitude) {
        attractions.push({
          ...attraction,
          dayIndex,
          attrIndex
        })
      }
    })
  })

  return attractions
}

const renderFallbackMap = () => {
  const container = document.getElementById('amap-container')
  if (!container) return

  const attractions = collectAttractions()
  if (!attractions.length) {
    container.innerHTML = '<div class="fallback-map empty">暂无可用坐标</div>'
    return
  }

  const lngs = attractions.map(item => item.location.longitude)
  const lats = attractions.map(item => item.location.latitude)
  const minLng = Math.min(...lngs)
  const maxLng = Math.max(...lngs)
  const minLat = Math.min(...lats)
  const maxLat = Math.max(...lats)
  const lngRange = maxLng - minLng || 0.01
  const latRange = maxLat - minLat || 0.01

  const pins = attractions.map((item, index) => {
    const left = 10 + ((item.location.longitude - minLng) / lngRange) * 80
    const top = 86 - ((item.location.latitude - minLat) / latRange) * 72
    return `
      <div class="fallback-pin" style="left:${left}%;top:${top}%">
        <span>${index + 1}</span>
        <strong>${item.name}</strong>
      </div>
    `
  }).join('')

  container.innerHTML = `
    <div class="fallback-map">
      <div class="fallback-map-grid"></div>
      <div class="fallback-map-title">坐标示意图</div>
      ${pins}
    </div>
  `
}

// 初始化地图
const initMap = async () => {
  const mapKey = import.meta.env.VITE_AMAP_WEB_JS_KEY
  if (!mapKey) {
    renderFallbackMap()
    return
  }

  try {
    const AMap = await AMapLoader.load({
      key: mapKey,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    map = new AMap.Map('amap-container', {
      zoom: 12,
      center: [116.397128, 39.916527],
      viewMode: '2D'
    })

    addAttractionMarkers(AMap)
  } catch (error) {
    console.error('地图加载失败:', error)
    renderFallbackMap()
  }
}

// 添加景点标记
const addAttractionMarkers = (AMap: any) => {
  if (!tripPlan.value) return

  const markers: any[] = []
  const allAttractions = collectAttractions()

  // 创建标记
  allAttractions.forEach((attraction, index) => {
    const marker = new AMap.Marker({
      position: [attraction.location.longitude, attraction.location.latitude],
      title: attraction.name,
      label: {
        content: `<div style="background: #8a5a2b; color: white; padding: 4px 8px; border-radius: 0; font-size: 12px;">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })

    // 创建信息窗口
    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding: 10px;">
          <h4 style="margin: 0 0 8px 0;">${attraction.name}</h4>
          <p style="margin: 4px 0;"><strong>地址:</strong> ${attraction.address}</p>
          <p style="margin: 4px 0;"><strong>游览时长:</strong> ${attraction.visit_duration}分钟</p>
          <p style="margin: 4px 0;"><strong>描述:</strong> ${attraction.description}</p>
          <p style="margin: 4px 0; color: #8a5a2b;"><strong>第${attraction.dayIndex + 1}天 景点${attraction.attrIndex + 1}</strong></p>
        </div>
      `,
      offset: new AMap.Pixel(0, -30)
    })

    // 点击标记显示信息窗口
    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition())
    })

    markers.push(marker)
  })

  // 添加标记到地图
  map.add(markers)

  // 自动调整视野以包含所有标记
  if (allAttractions.length > 0) {
    map.setFitView(markers)
  }

  // 绘制路线
  drawRoutes(AMap, allAttractions)
}

// 绘制路线
const drawRoutes = (AMap: any, attractions: any[]) => {
  if (attractions.length < 2) return

  // 按天分组绘制路线
  const dayGroups: any = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) {
      dayGroups[attr.dayIndex] = []
    }
    dayGroups[attr.dayIndex].push(attr)
  })

  // 为每天的景点绘制路线
  Object.values(dayGroups).forEach((dayAttractions: any) => {
    if (dayAttractions.length < 2) return

    const path = dayAttractions.map((attr: any) => [
      attr.location.longitude,
      attr.location.latitude
    ])

    const polyline = new AMap.Polyline({
      path: path,
      strokeColor: '#8a5a2b',
      strokeWeight: 4,
      strokeOpacity: 0.8,
      strokeStyle: 'solid',
      showDir: true // 显示方向箭头
    })

    map.add(polyline)
  })
}
</script>

<style scoped>
.result-container {
  min-height: calc(100vh - 56px);
  padding: 28px 32px 64px;
  background:
    linear-gradient(90deg, rgba(32, 38, 44, 0.035) 1px, transparent 1px),
    #ece8df;
  background-size: 52px 100%;
}

.page-header {
  max-width: 1360px;
  margin: 0 auto 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.text-button {
  padding: 8px 0;
  border: 0;
  background: transparent;
  color: #51483e;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}

.text-button:hover {
  color: #8a5a2b;
}

.page-actions {
  display: flex;
  gap: 8px;
}

.page-actions :deep(.ant-btn) {
  border-radius: 0;
  box-shadow: none;
}

.content-wrapper {
  max-width: 1360px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 24px;
}

.nav-sheet {
  padding: 18px 12px 12px;
  border-top: 4px solid #8a5a2b;
  background: #fbfaf6;
}

.nav-sheet > p {
  margin: 0 12px 10px;
  color: #8a5a2b;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.12em;
}

.side-nav :deep(.ant-menu) {
  border: 0 !important;
  background: transparent;
}

.side-nav :deep(.ant-menu-item),
.side-nav :deep(.ant-menu-submenu-title) {
  height: 38px;
  margin: 0 !important;
  border-radius: 0;
  color: #50483f;
  font-size: 13px;
  line-height: 38px;
}

.side-nav :deep(.ant-menu-item-selected) {
  background: #ede6db;
  color: #5f3a17;
  font-weight: 700;
}

.main-content {
  min-width: 0;
}

.trip-hero {
  display: grid;
  grid-template-columns: minmax(280px, 0.75fr) minmax(360px, 1.25fr);
  gap: 64px;
  align-items: end;
  min-height: 250px;
  padding: 38px 42px;
  background: #20262c;
  color: #fffdf8;
}

.section-kicker {
  margin: 0 0 20px;
  color: #c7a47a;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.18em;
}

.trip-hero h1 {
  margin: 0;
  font-family: var(--font-serif-cn);
  font-size: clamp(56px, 7vw, 92px);
  font-weight: 600;
  letter-spacing: 0.04em;
  line-height: 0.95;
}

.trip-date {
  margin: 22px 0 0;
  color: #d5cec4;
  font-size: 14px;
  letter-spacing: 0.06em;
}

.editor-note {
  padding: 0 0 4px 24px;
  border-left: 1px solid #6d675f;
}

.editor-note span,
.detail-label {
  display: block;
  margin-bottom: 10px;
  color: #c7a47a;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.12em;
}

.editor-note p {
  margin: 0;
  color: #eee9e1;
  font-family: var(--font-serif-cn);
  font-size: 17px;
  line-height: 1.85;
}

.top-info-section {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  border: 1px solid #d5cbbb;
  border-top: 0;
  background: #fbfaf6;
}

.budget-sheet {
  padding: 30px;
  border-right: 1px solid #d5cbbb;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.section-heading > span {
  padding-top: 2px;
  color: #8a5a2b;
  font-size: 12px;
  font-weight: 800;
}

.section-heading p {
  margin: 0 0 4px;
  color: #897766;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.16em;
}

.section-heading h2 {
  margin: 0;
  color: #20262c;
  font-family: var(--font-serif-cn);
  font-size: 26px;
  font-weight: 600;
}

.budget-list {
  margin-top: 28px;
  border-top: 1px solid #ddd4c6;
}

.budget-list > div {
  display: flex;
  justify-content: space-between;
  padding: 13px 2px;
  border-bottom: 1px solid #e4ddd2;
}

.budget-list span {
  color: #70665b;
  font-size: 13px;
}

.budget-list strong {
  color: #2f3439;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.budget-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 24px;
  color: #5f3a17;
}

.budget-total span {
  font-size: 13px;
}

.budget-total strong {
  font-family: var(--font-serif-cn);
  font-size: 34px;
  font-weight: 600;
}

.map-sheet {
  position: relative;
  min-height: 440px;
  padding-top: 72px;
  background: #262d33;
}

.map-sheet .section-heading {
  position: absolute;
  z-index: 2;
  top: 20px;
  left: 24px;
}

.section-heading.light h2 {
  color: #fffdf8;
}

.section-heading.light p {
  color: #aaa49b;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 368px;
}

:deep(.fallback-map) {
  position: relative;
  min-height: 368px;
  height: 100%;
  overflow: hidden;
  background: #ded5c8;
}

:deep(.fallback-map.empty) {
  display: grid;
  place-items: center;
  color: #685d50;
}

:deep(.fallback-map-grid) {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(95, 58, 23, 0.12) 1px, transparent 1px),
    linear-gradient(180deg, rgba(95, 58, 23, 0.12) 1px, transparent 1px);
  background-size: 34px 34px;
}

:deep(.fallback-map-title) {
  position: absolute;
  top: 16px;
  left: 18px;
  padding: 6px 9px;
  border: 1px solid #c8bba8;
  background: rgba(251, 250, 246, 0.92);
  color: #5f3a17;
  font-size: 12px;
}

:deep(.fallback-pin) {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 6px;
  transform: translate(-50%, -50%);
}

:deep(.fallback-pin span) {
  display: grid;
  place-items: center;
  width: 25px;
  height: 25px;
  background: #8a5a2b;
  color: white;
  font-size: 11px;
  font-weight: 800;
}

:deep(.fallback-pin strong) {
  padding: 4px 7px;
  border: 1px solid #c8bba8;
  background: rgba(251, 250, 246, 0.92);
  color: #20262c;
  font-size: 11px;
  white-space: nowrap;
}

.days-section,
.weather-section {
  margin-top: 20px;
  padding: 34px;
  border: 1px solid #d5cbbb;
  background: #fbfaf6;
}

.days-heading {
  margin-bottom: 24px;
}

:deep(.ant-collapse) {
  border: 0;
  border-radius: 0;
  background: transparent;
}

:deep(.ant-collapse-item) {
  border: 0 !important;
  border-top: 1px solid #cfc4b4 !important;
  border-radius: 0 !important;
}

:deep(.ant-collapse-item:last-child) {
  border-bottom: 1px solid #cfc4b4 !important;
}

:deep(.ant-collapse-header) {
  align-items: center !important;
  padding: 20px 4px !important;
  background: transparent;
}

:deep(.ant-collapse-content) {
  border-top: 1px solid #e1d9cd;
  background: transparent;
}

:deep(.ant-collapse-content-box) {
  padding: 26px 4px 34px !important;
}

.day-header {
  width: 100%;
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) 110px;
  gap: 18px;
  align-items: center;
  padding-right: 10px;
}

.day-number {
  color: #8a5a2b;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.day-header strong {
  overflow: hidden;
  color: #252b30;
  font-family: var(--font-serif-cn);
  font-size: 19px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.day-header time {
  color: #80756a;
  font-size: 12px;
  text-align: right;
}

.day-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin-bottom: 22px;
  border: 1px solid #ddd4c7;
}

.day-meta > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 15px;
}

.day-meta > div + div {
  border-left: 1px solid #ddd4c7;
}

.day-meta span {
  color: #8a7d70;
  font-size: 10px;
}

.day-meta strong {
  color: #34383c;
  font-size: 13px;
  font-weight: 650;
}

.route-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.place-entry {
  min-width: 0;
  border: 1px solid #d9d0c3;
  background: #fff;
}

.attraction-image-wrapper {
  position: relative;
  height: 210px;
  overflow: hidden;
  background: #d9d1c6;
}

.attraction-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: saturate(0.82) contrast(0.96);
  transition: transform 450ms ease;
}

.place-entry:hover .attraction-image {
  transform: scale(1.025);
}

.attraction-badge,
.price-tag {
  position: absolute;
  top: 12px;
  background: #20262c;
  color: white;
  font-size: 11px;
  font-weight: 750;
}

.attraction-badge {
  left: 12px;
  padding: 7px 8px;
  letter-spacing: 0.08em;
}

.price-tag {
  right: 12px;
  padding: 7px 9px;
}

.place-copy {
  padding: 18px 20px 20px;
}

.place-title-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.place-copy h3,
.stay-note h3 {
  margin: 0;
  color: #20262c;
  font-family: var(--font-serif-cn);
  font-size: 21px;
  font-weight: 600;
}

.place-meta {
  margin: 10px 0 0;
  color: #89796a;
  font-size: 11px;
  line-height: 1.6;
}

.place-description {
  margin: 12px 0 0;
  color: #514a43;
  font-size: 13px;
  line-height: 1.75;
}

.edit-actions {
  display: flex;
  gap: 4px;
}

.place-copy label {
  display: grid;
  gap: 6px;
  margin-top: 12px;
  color: #70665b;
  font-size: 12px;
}

.day-details {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.stay-note,
.meal-note {
  padding: 22px;
  border: 1px solid #d9d0c3;
  background: #f5f0e8;
}

.stay-note > p:not(.detail-label) {
  margin: 10px 0 5px;
  color: #50483f;
  font-size: 13px;
}

.stay-note small {
  color: #84796e;
  line-height: 1.6;
}

.meal-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  padding: 9px 0;
  border-top: 1px solid #ddd3c4;
}

.meal-row > span {
  color: #8a5a2b;
  font-size: 11px;
}

.meal-row p {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin: 0;
}

.meal-row strong {
  color: #34383c;
  font-size: 13px;
}

.meal-row small {
  color: #7d7267;
  font-size: 11px;
  line-height: 1.5;
}

.weather-section .section-heading {
  margin-bottom: 22px;
}

.weather-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-top: 1px solid #d8cfc2;
}

.weather-list article {
  display: grid;
  gap: 7px;
  padding: 18px 16px;
  border-bottom: 1px solid #d8cfc2;
}

.weather-list article:not(:nth-child(3n + 1)) {
  border-left: 1px solid #d8cfc2;
}

.weather-list time,
.weather-list small {
  color: #84786c;
  font-size: 11px;
}

.weather-list strong {
  color: #33383d;
  font-family: var(--font-serif-cn);
  font-size: 17px;
  font-weight: 600;
}

.weather-list span {
  color: #8a5a2b;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.empty-state {
  max-width: 600px;
  margin: 120px auto;
  padding: 60px;
  border: 1px solid #d5cbbb;
  background: #fbfaf6;
  text-align: center;
}

.back-top-button {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  background: #20262c;
  color: white;
  font-size: 18px;
}

@media (prefers-reduced-motion: reduce) {
  * {
    scroll-behavior: auto !important;
    transition: none !important;
  }
}

@media (max-width: 1050px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }

  .side-nav {
    display: none;
  }
}

@media (max-width: 760px) {
  .result-container {
    padding: 16px 10px 44px;
  }

  .page-header {
    align-items: flex-start;
  }

  .page-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .trip-hero {
    grid-template-columns: 1fr;
    gap: 32px;
    min-height: 0;
    padding: 30px 24px;
  }

  .trip-hero h1 {
    font-size: 54px;
  }

  .editor-note {
    padding-left: 16px;
  }

  .top-info-section,
  .route-grid,
  .day-details {
    grid-template-columns: 1fr;
  }

  .budget-sheet {
    border-right: 0;
    border-bottom: 1px solid #d5cbbb;
  }

  .days-section,
  .weather-section {
    padding: 24px 18px;
  }

  .day-header {
    grid-template-columns: 70px minmax(0, 1fr);
  }

  .day-header time {
    display: none;
  }

  .day-meta {
    grid-template-columns: 1fr;
  }

  .day-meta > div + div {
    border-top: 1px solid #ddd4c7;
    border-left: 0;
  }

  .weather-list {
    grid-template-columns: 1fr;
  }

  .weather-list article:not(:nth-child(3n + 1)) {
    border-left: 0;
  }
}

@media (max-width: 460px) {
  .text-button {
    font-size: 12px;
  }

  .page-actions :deep(.ant-btn) {
    padding-inline: 9px;
    font-size: 12px;
  }

  .place-title-row {
    display: block;
  }

  .edit-actions {
    margin-top: 12px;
  }
}
</style>
