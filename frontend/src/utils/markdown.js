/**
 * 安全 Markdown 渲染
 * 使用 DOMPurify 过滤所有危险HTML标签和属性，防止XSS攻击
 */
import DOMPurify from 'dompurify'

// 配置 DOMPurify：仅允许报告渲染需要的标签和属性
const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'em', 'b', 'i',
    'ul', 'ol', 'li',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'br', 'p', 'span', 'div', 'hr',
    'blockquote', 'pre', 'code',
    'a',
  ],
  ALLOWED_ATTR: ['style', 'colspan', 'rowspan', 'href', 'target', 'rel'],
  // 明确禁止的危险标签和属性
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'textarea', 'button', 'meta', 'link'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'onsubmit', 'ontoggle', 'onanimationend'],
  // 保持实体编码
  KEEP_CONTENT: true,
}

export function marked(text) {
  if (!text) return ''
  let html = text
  // 标题
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // 粗体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 斜体
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // 无序列表
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  // 表格
  html = html.replace(/^\|(.+)\|$/gm, (match) => {
    const cells = match.split('|').filter(c => c.trim())
    if (cells.every(c => /^[\s-:]+$/.test(c))) return ''
    const tag = 'td'
    return '<tr>' + cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('') + '</tr>'
  })
  html = html.replace(/(<tr>.*<\/tr>\n?)+/g, '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">$&</table>')
  // 换行
  html = html.replace(/\n\n/g, '<br><br>')
  html = html.replace(/\n/g, '<br>')

  // ★ 安全过滤：移除所有危险标签（script/iframe/onerror等）
  return DOMPurify.sanitize(html, PURIFY_CONFIG)
}
