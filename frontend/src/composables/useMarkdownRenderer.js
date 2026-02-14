import { computed, isRef } from 'vue'
import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
// Import only highlight.js core + commonly used languages for smaller bundle
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import bash from 'highlight.js/lib/languages/bash'
import json from 'highlight.js/lib/languages/json'
import css from 'highlight.js/lib/languages/css'
import xml from 'highlight.js/lib/languages/xml'
import sql from 'highlight.js/lib/languages/sql'
import markdown from 'highlight.js/lib/languages/markdown'
import yaml from 'highlight.js/lib/languages/yaml'
import plaintext from 'highlight.js/lib/languages/plaintext'
import go from 'highlight.js/lib/languages/go'
import rust from 'highlight.js/lib/languages/rust'
import java from 'highlight.js/lib/languages/java'
import c from 'highlight.js/lib/languages/c'
import cpp from 'highlight.js/lib/languages/cpp'
import php from 'highlight.js/lib/languages/php'
import ruby from 'highlight.js/lib/languages/ruby'
import DOMPurify from 'dompurify'
import { isImageFile, getFileName } from './useFileDetection'
import { useWorkspaceState } from './state'

// Register languages
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('js', javascript)
hljs.registerLanguage('typescript', typescript)
hljs.registerLanguage('ts', typescript)
hljs.registerLanguage('python', python)
hljs.registerLanguage('py', python)
hljs.registerLanguage('bash', bash)
hljs.registerLanguage('sh', bash)
hljs.registerLanguage('shell', bash)
hljs.registerLanguage('json', json)
hljs.registerLanguage('css', css)
hljs.registerLanguage('xml', xml)
hljs.registerLanguage('html', xml)
hljs.registerLanguage('sql', sql)
hljs.registerLanguage('markdown', markdown)
hljs.registerLanguage('md', markdown)
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('yml', yaml)
hljs.registerLanguage('plaintext', plaintext)
hljs.registerLanguage('text', plaintext)
hljs.registerLanguage('go', go)
hljs.registerLanguage('golang', go)
hljs.registerLanguage('rust', rust)
hljs.registerLanguage('rs', rust)
hljs.registerLanguage('java', java)
hljs.registerLanguage('c', c)
hljs.registerLanguage('cpp', cpp)
hljs.registerLanguage('c++', cpp)
hljs.registerLanguage('php', php)
hljs.registerLanguage('ruby', ruby)
hljs.registerLanguage('rb', ruby)

// Configure marked with highlight extension (only once)
let isConfigured = false

function configureMarked() {
    if (isConfigured) return

    marked.use(markedHighlight({
        langPrefix: 'hljs language-',
        highlight(code, lang) {
            try {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value
                }
                return code
            } catch (e) {
                console.error('Highlight error:', e)
                return code
            }
        }
    }))

    marked.setOptions({
        breaks: true,
        gfm: true
    })

    isConfigured = true
}

// Helper to escape HTML for safe display
function escapeHtml(text) {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
}

// Helper to create file badge HTML
function createFileBadge(fileName, fullPath, isImage, isDirectory = false) {
    let bgColor, hoverColor, icon
    if (isDirectory) {
        bgColor = 'bg-amber-500/20 border-amber-500/40'
        hoverColor = 'hover:bg-amber-500/30'
        icon = '📁'
    } else if (isImage) {
        bgColor = 'bg-green-500/20 border-green-500/40'
        hoverColor = 'hover:bg-green-500/30'
        icon = '🖼️'
    } else {
        bgColor = 'bg-blue-500/20 border-blue-500/40'
        hoverColor = 'hover:bg-blue-500/30'
        icon = '📄'
    }
    return `<span class="file-link inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded ${bgColor} border ${hoverColor} cursor-pointer transition-all" data-file-path="${fullPath}"><span>${icon}</span><span>${fileName}</span></span>`
}

/**
 * Composable for rendering markdown with syntax highlighting and file badges
 *
 * @param {Object|Ref<Object>|Function} messageSource - message object, ref, or getter function
 */
export function useMarkdownRenderer(messageSource) {
    // Ensure marked is configured
    configureMarked()

    // Get workspace state to check if files exist
    const { flattenFiles, artifacts } = useWorkspaceState()

    const renderedContent = computed(() => {
        // Handle different input types: ref, getter function, or plain object
        let msg
        if (isRef(messageSource)) {
            msg = messageSource.value
        } else if (typeof messageSource === 'function') {
            msg = messageSource()
        } else {
            msg = messageSource
        }

        if (!msg?.text) return ''

        // Get flat list of existing files for checking
        // Note: explicitly access artifacts.value to ensure Vue tracks this dependency
        const existingFiles = flattenFiles(artifacts.value)
        const existingFileNames = new Set(existingFiles.map(f => f.name?.toLowerCase()))
        const existingFilePaths = new Set(existingFiles.map(f => f.path?.toLowerCase()))

        // Helper to check if file exists in workspace
        const fileExists = (fileName) => {
            const lower = fileName.toLowerCase()
            return existingFileNames.has(lower) || existingFilePaths.has(lower)
        }

        // For AI messages, parse file references and render as badges
        if (msg.role !== 'user') {
            try {
                // Parse markdown
                let html = marked.parse(msg.text)

                // Detect /workspace paths and make them clickable (always show these)
                const workspacePattern = /(<code>)?\/workspace(\/[^\s)<`]*)?(\/)?(<\/code>)?/g
                html = html.replace(workspacePattern, (match, codeStart, pathPart, trailingSlash, codeEnd) => {
                    let fullPath = '/workspace' + (pathPart || '') + (trailingSlash || '')
                    fullPath = fullPath.replace(/[.,;:!?]+$/, '')

                    const isDirectory = fullPath.endsWith('/') || !fullPath.split('/').pop().includes('.')
                    const displayName = fullPath.split('/').filter(Boolean).pop() || 'workspace'
                    const isImage = !isDirectory && isImageFile(displayName)

                    return createFileBadge(displayName, fullPath, isImage, isDirectory)
                })

                // Detect filenames inside <strong> or <code> tags - ONLY if file exists
                // Handles quotes (both literal " and HTML-encoded &quot;) and paths with slashes
                const taggedFilePattern = /<(strong|code)>(?:"|&quot;)?([\w./_-]+\.[a-zA-Z0-9]+)(?:"|&quot;)?<\/(strong|code)>/gi
                html = html.replace(taggedFilePattern, (match, openTag, fileName) => {
                    // Only create badge if file exists in workspace
                    if (!fileExists(fileName)) {
                        return match // Keep original formatting
                    }
                    const isImage = isImageFile(fileName)
                    return createFileBadge(fileName, fileName, isImage)
                })

                // Detect @filename patterns - ONLY if file exists
                const filePattern = /(?<![a-zA-Z0-9])@([^\s@<]+\.[a-zA-Z0-9]+)/g
                html = html.replace(filePattern, (match, fileName) => {
                    // Skip common email domains
                    const emailDomains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'mail.com', 'protonmail.com']
                    if (emailDomains.includes(fileName.toLowerCase())) return match

                    // Only create badge if file exists in workspace
                    if (!fileExists(fileName)) {
                        return match // Keep original @filename
                    }
                    const isImage = isImageFile(fileName)
                    return createFileBadge(`@${fileName}`, fileName, isImage)
                })

                // Add target="_blank" to all external links (open in new tab)
                html = html.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a target="_blank" rel="noopener noreferrer" href="$1"')

                // Configure DOMPurify to allow data-file-path and target/rel attributes
                return DOMPurify.sanitize(html, { ADD_ATTR: ['data-file-path', 'target', 'rel'] })
            } catch (e) {
                console.error('Markdown parse error:', e)
                return `<pre>${escapeHtml(msg.text)}</pre>`
            }
        }

        try {
            // Parse markdown
            let html = marked.parse(msg.text)
            // Add target="_blank" to all external links (open in new tab)
            html = html.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a target="_blank" rel="noopener noreferrer" href="$1"')
            return DOMPurify.sanitize(html, { ADD_ATTR: ['target', 'rel'] })
        } catch (e) {
            console.error('Markdown parse error:', e)
            return `<pre>${escapeHtml(msg.text)}</pre>`
        }
    })

    return {
        renderedContent,
        isImageFile,
        getFileName,
        escapeHtml
    }
}

// Export utilities for use without the full composable (re-export from useFileDetection for backwards compatibility)
export { isImageFile, getFileName, escapeHtml }
