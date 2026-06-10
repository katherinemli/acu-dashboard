<template>
  <div class="docs-layout">

    <aside class="docs-toc">
      <div class="toc-title">Contents</div>
      <nav>
        <a
          v-for="h in headings"
          :key="h.id"
          href="#"
          class="toc-link"
          :class="'toc-h' + h.level"
          @click.prevent="scrollTo(h.id)"
        >{{ h.text }}</a>
      </nav>
    </aside>

    <main class="docs-content" ref="contentEl" @click="onContentClick">
      <div v-if="loading" class="docs-loading">Loading documentation...</div>
      <div v-else-if="error" class="docs-error">{{ error }}</div>
      <div v-else v-html="renderedHtml" class="docs-body"></div>
    </main>

  </div>
</template>

<script>
import axios from 'axios'
import { marked } from 'marked'

const API_URL = import.meta.env.VITE_API_URL || ''

export default {
  name: 'Docs',
  data() {
    return {
      loading: true,
      error: null,
      rawMarkdown: '',
      headings: [],
    }
  },
  computed: {
    renderedHtml() {
      if (!this.rawMarkdown) return ''

      // Rewrite relative screenshot paths to the API endpoint
      const md = this.rawMarkdown.replace(
        /!\[([^\]]*)\]\(screenshots\/([^)]+)\)/g,
        (_, alt, file) => `![${alt}](${API_URL}/api/docs/screenshots/${file})`
      )

      const html = marked.parse(md)

      // Extract headings for TOC (after render so we get IDs)
      this.$nextTick(() => this._buildToc())
      return html
    },
  },
  methods: {
    async fetchDocs() {
      try {
        const res = await axios.get(`${API_URL}/api/docs/content`)
        this.rawMarkdown = res.data.content
      } catch (e) {
        this.error = e.response?.data?.error || 'Could not load documentation.'
      } finally {
        this.loading = false
      }
    },
    scrollTo(id) {
      const el = document.getElementById(id)
      if (el) el.scrollIntoView({ behavior: 'smooth' })
    },
    onContentClick(e) {
      const a = e.target.closest('a[href^="#"]')
      if (!a) return
      e.preventDefault()
      const id = a.getAttribute('href').slice(1)
      this.scrollTo(id)
    },
    _buildToc() {
      if (!this.$refs.contentEl) return
      const nodes = this.$refs.contentEl.querySelectorAll('h1, h2, h3')
      this.headings = Array.from(nodes).map(el => {
        if (!el.id) {
          el.id = el.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
        }
        return { id: el.id, text: el.textContent, level: parseInt(el.tagName[1]) }
      })
    },
  },
  mounted() {
    this.fetchDocs()
  },
}
</script>

<style scoped>
.docs-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ── TOC sidebar ── */
.docs-toc {
  width: 220px;
  min-width: 220px;
  background: #1e3a5f;
  padding: 20px 0;
  overflow-y: auto;
  border-right: 1px solid rgba(255,255,255,0.08);
}

.toc-title {
  color: #aac4e0;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0 16px 12px;
}

.toc-link {
  display: block;
  color: #cdd8e6;
  text-decoration: none;
  font-size: 12px;
  padding: 4px 16px;
  line-height: 1.4;
  transition: background 0.15s, color 0.15s;
}

.toc-link:hover {
  background: rgba(255,255,255,0.07);
  color: #fff;
}

.toc-h1 { font-weight: 700; color: #fff; padding-left: 16px; }
.toc-h2 { padding-left: 16px; }
.toc-h3 { padding-left: 28px; font-size: 11px; color: #9ab4cc; }

/* ── Main content ── */
.docs-content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
  background: #f8fafc;
}

.docs-loading,
.docs-error {
  color: #888;
  font-size: 14px;
  margin-top: 40px;
  text-align: center;
}

.docs-error { color: #e05; }

/* ── Markdown body styles ── */
.docs-body :deep(h1) {
  font-size: 26px;
  font-weight: 700;
  color: #1a2e4a;
  margin: 0 0 8px;
  padding-bottom: 8px;
  border-bottom: 2px solid #dde6f0;
}

.docs-body :deep(h2) {
  font-size: 20px;
  font-weight: 700;
  color: #1a2e4a;
  margin: 36px 0 10px;
  padding-bottom: 5px;
  border-bottom: 1px solid #e2eaf3;
}

.docs-body :deep(h3) {
  font-size: 15px;
  font-weight: 700;
  color: #2c4a6e;
  margin: 24px 0 8px;
}

.docs-body :deep(p) {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  margin: 0 0 12px;
}

.docs-body :deep(ul), .docs-body :deep(ol) {
  font-size: 14px;
  line-height: 1.7;
  color: #334155;
  margin: 0 0 12px;
  padding-left: 24px;
}

.docs-body :deep(li) { margin-bottom: 3px; }

.docs-body :deep(strong) { color: #1a2e4a; }

.docs-body :deep(code) {
  background: #e8eef5;
  color: #1a3a5c;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  font-family: monospace;
}

.docs-body :deep(pre) {
  background: #1e3a5f;
  color: #cdd8e6;
  padding: 14px 18px;
  border-radius: 5px;
  font-size: 12px;
  overflow-x: auto;
  margin: 0 0 16px;
}

.docs-body :deep(pre code) {
  background: none;
  color: inherit;
  padding: 0;
}

.docs-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin: 0 0 16px;
}

.docs-body :deep(th) {
  background: #1e3a5f;
  color: #fff;
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
}

.docs-body :deep(td) {
  padding: 7px 12px;
  border-bottom: 1px solid #e2eaf3;
  color: #334155;
  vertical-align: top;
}

.docs-body :deep(tr:nth-child(even) td) { background: #f1f6fb; }

.docs-body :deep(img) {
  max-width: 100%;
  border: 1px solid #dde6f0;
  border-radius: 5px;
  margin: 10px 0 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.docs-body :deep(blockquote) {
  border-left: 3px solid #4a90d9;
  background: #eef4fb;
  margin: 0 0 14px;
  padding: 10px 16px;
  border-radius: 0 4px 4px 0;
  font-size: 13px;
  color: #2c4a6e;
}

.docs-body :deep(hr) {
  border: none;
  border-top: 1px solid #dde6f0;
  margin: 28px 0;
}
</style>
