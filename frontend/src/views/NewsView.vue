<template>
  <div class="news-view">
    <div class="page-header">
      <h2>市场资讯</h2>
      <div class="news-tabs">
        <button
          v-for="cat in categories"
          :key="cat.key"
          :class="['tab-btn', { active: activeCat === cat.key }]"
          @click="activeCat = cat.key"
        >{{ cat.label }}</button>
      </div>
    </div>

    <div class="timeline">
      <div class="timeline-group" v-for="(group, gidx) in filteredNews" :key="gidx">
        <!-- 日期分隔头 -->
        <div class="date-header">{{ group.date }}</div>

        <!-- 时间线区域 -->
        <div class="timeline-track">
          <!-- 竖线 -->
          <div class="tl-line"></div>
          <!-- 每条资讯 -->
          <article
            v-for="item in group.items"
            :key="item.id"
            class="tl-item"
            @click="openNews(item)"
          >
            <div class="tl-dot">
              <span class="dot-time">{{ item.time }}</span>
            </div>
            <div class="tl-card">
              <div class="news-tags">
                <el-tag
                  v-for="tag in item.tags" :key="tag"
                  size="small"
                  :type="tagType(tag)"
                  class="news-tag"
                >{{ tag }}</el-tag>
              </div>
              <h3 class="news-title">{{ item.title }}</h3>
              <p class="news-summary caption">{{ item.summary }}</p>
              <div class="news-footer">
                <span class="news-source caption">{{ item.source }}</span>
              </div>
            </div>
          </article>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const activeCat = ref('all')

const categories = [
  { key: 'all', label: '全部' },
  { key: 'macro', label: '宏观' },
  { key: 'stock', label: '股市' },
  { key: 'fund', label: '基金' },
  { key: 'industry', label: '行业' },
]

interface NewsItem {
  id: string; title: string; summary: string; source: string
  time: string; tags: string[]; url: string
}

const newsData: NewsItem[] = [
  { id: '1', title: '央行宣布下调存款准备金率0.5个百分点', summary: '中国人民银行决定自2026年5月15日起下调金融机构存款准备金率0.5个百分点，释放长期资金约1万亿元。', source: '中国人民银行', time: '10:32', tags: ['宏观', '政策'], url: '#' },
  { id: '2', title: 'A股三大指数集体收涨 沪指重返3300点', summary: '今日A股市场全线走强，上证指数收涨1.25%报3356.78点，深证成指涨1.12%，创业板指涨0.85%。两市成交额超1.2万亿。', source: '东方财富', time: '15:05', tags: ['股市'], url: '#' },
  { id: '3', title: '北向资金今日净买入超80亿元', summary: '北向资金今日大幅净买入82.56亿元，其中沪股通净买入45.23亿元，深股通净买入37.33亿元。贵州茅台、宁德时代获净买入居前。', source: 'Wind', time: '15:30', tags: ['股市', '资金'], url: '#' },
  { id: '4', title: '多家基金公司宣布自购旗下权益基金', summary: '包括易方达、华夏、南方在内的多家头部基金公司宣布自购旗下权益类基金，合计自购金额超过10亿元，释放积极信号。', source: '中国基金报', time: '14:20', tags: ['基金'], url: '#' },
  { id: '5', title: '新能源板块持续活跃 光伏产业链领涨', summary: '新能源板块今日表现强势，光伏产业链集体走强，隆基绿能涨超5%，通威股份涨超4%。消息面上，多部门发布支持新能源发展的相关政策。', source: '证券时报', time: '11:45', tags: ['行业', '新能源'], url: '#' },
  { id: '6', title: '美联储维持利率不变 符合市场预期', summary: '美联储最新议息会议决定维持联邦基金利率目标区间不变，并表示将继续关注通胀数据。市场普遍预计年内可能降息1-2次。', source: '新华社', time: '08:15', tags: ['宏观', '海外'], url: '#' },
  { id: '7', title: '半导体行业景气度回升 存储芯片价格反弹', summary: '据行业研究机构数据，存储芯片价格连续两个月环比上涨，DRAM和NAND Flash涨幅分别达到5%和3%，行业复苏信号明显。', source: '集微网', time: '09:30', tags: ['行业', '半导体'], url: '#' },
  { id: '8', title: '2026年Q1公募基金持仓分析：加仓科技减仓消费', summary: '2026年一季度公募基金持仓数据出炉，前十大重仓股中科技股占比提升至35%，消费股占比下降至22%，新能源、半导体获显著加仓。', source: '天天基金网', time: '13:00', tags: ['基金', '分析'], url: '#' },
]

const groupedData = [
  { date: '今天 5月8日', items: newsData.slice(0, 4) },
  { date: '昨天 5月7日', items: newsData.slice(4, 6) },
  { date: '5月6日', items: newsData.slice(6, 8) },
]

const filteredNews = computed(() => {
  if (activeCat.value === 'all') return groupedData
  return groupedData.map(g => ({
    date: g.date,
    items: g.items.filter(item =>
      item.tags.some(t => t === activeCat.value)
    ),
  })).filter(g => g.items.length > 0)
})

function openNews(item: NewsItem) {
  window.open(item.url, '_blank')
}

function tagType(tag: string) {
  const map: Record<string, string> = {
    '宏观': 'danger', '政策': 'danger',
    '股市': 'primary', '资金': 'primary',
    '基金': 'success', '行业': 'warning',
    '分析': 'info',
  }
  return map[tag] || 'info'
}
</script>

<style scoped lang="scss">
.news-view {
  max-width: 860px;
  margin: 0 auto;
  padding: $spacing-lg;
}

.page-header {
  margin-bottom: $spacing-xl;

  h2 { margin-bottom: $spacing-md; }
}

.news-tabs {
  display: flex;
  gap: $spacing-xs;

  .tab-btn {
    padding: 8px 20px;
    border: 1px solid $hairline;
    background: $canvas;
    border-radius: $rounded-pill;
    font-size: 14px;
    color: $ink-muted-48;
    cursor: pointer;
    transition: all 0.2s;

    &:hover { border-color: $primary; color: $primary; }
    &.active { background: $primary; border-color: $primary; color: white; }
  }
}

/* 时间线 */
.timeline-group {
  margin-bottom: $spacing-lg;
}

.date-header {
  position: relative;
  z-index: 2;
  display: inline-block;
  padding: 4px 16px;
  background: $canvas-parchment;
  border: 1px solid $divider-soft;
  border-radius: $rounded-pill;
  font-size: 13px;
  font-weight: 600;
  color: $ink-muted-48;
  margin-bottom: $spacing-md;
}

.timeline-track {
  position: relative;
  padding-left: 64px;  /* 留给时间和竖线的空间 */
}

/* 竖线 - 从第一个item延伸到最后一个 */
.tl-line {
  position: absolute;
  left: 30px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: linear-gradient(to bottom,
    $hairline 0%,
    $primary 30%,
    $primary 70%,
    $hairline 100%
  );
  opacity: 0.5;
}

/* 每条资讯 */
.tl-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;
  margin-bottom: $spacing-md;
  cursor: pointer;

  &:last-child { margin-bottom: 0; }
}

/* 左侧圆点 + 时间 */
.tl-dot {
  position: absolute;
  left: -64px;  /* 从padding起始处偏移 */
  top: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 64px;
  justify-content: flex-end;

  /* 圆点 */
  &::after {
    content: '';
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: $primary;
    border: 2px solid $canvas;
    box-shadow: 0 0 0 2px rgba(41,151,255,0.3);
    flex-shrink: 0;
    transition: all 0.2s;
  }

  .dot-time {
    font-size: 12px;
    font-family: $font-display;
    font-weight: 600;
    color: $ink-muted-48;
    white-space: nowrap;
    transition: color 0.2s;
  }
}

/* 悬停时圆点放大变色 */
.tl-item:hover {
  .tl-dot::after {
    transform: scale(1.3);
    background: #ff6b6b;
    box-shadow: 0 0 0 3px rgba(255,107,107,0.3);
  }
  .dot-time { color: $ink; font-weight: 700; }
}

/* 资讯卡片 */
.tl-card {
  flex: 1;
  background: $canvas;
  border: 1px solid $divider-soft;
  border-radius: $rounded-lg;
  padding: $spacing-md $spacing-lg;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-1px);
    box-shadow: $shadow-elevated;
    border-color: rgba(41,151,255,0.2);
  }

  .news-tags {
    display: flex;
    gap: 6px;
    margin-bottom: $spacing-xs;
  }

  .news-tag {
    border: none;
    font-weight: 500;
  }

  .news-title {
    font-size: 16px;
    font-weight: 600;
    line-height: 1.4;
    margin-bottom: $spacing-xs;
    color: $ink;

    &:hover { color: $primary; }
  }

  .news-summary {
    margin-bottom: $spacing-sm;
    line-height: 1.5;
    font-size: 13px;
    color: $ink-muted-48;
  }

  .news-footer {
    display: flex;
    justify-content: space-between;
    color: $ink-muted-48;
    font-size: 12px;
  }
}
</style>
