import { computed } from 'vue'
import {
    File as FileIcon,
    FileText,
    FileCode2,
    FileImage,
    FileSpreadsheet,
    FileArchive,
    FileAudio,
    FileVideo,
    FileCog,
    FileType,
    Braces
} from 'lucide-vue-next'

// File extensions categories
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico']
const DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'csv', 'json', 'xml', 'html', 'css', 'js', 'ts', 'py', 'md', 'zip', 'rar', 'mp3', 'mp4', 'wav', 'avi', 'mov']
const ALL_FILE_EXTENSIONS = [...IMAGE_EXTENSIONS, ...DOCUMENT_EXTENSIONS]

// Get extension from filename
function getExtension(filename) {
    if (!filename) return ''
    const parts = filename.split('.')
    return parts.length > 1 ? parts.pop().toLowerCase() : ''
}

// Check if file is an image
function isImageFile(filename) {
    const ext = getExtension(filename)
    return IMAGE_EXTENSIONS.includes(ext)
}

// Get filename from path
function getFileName(filePath) {
    return filePath?.split('/').pop() || filePath
}

// Get icon configuration for a file based on extension
function getFileIconConfig(filename) {
    const ext = getExtension(filename)

    // Code files - different colors for different languages
    if (['js', 'jsx', 'mjs'].includes(ext)) return { icon: FileCode2, color: 'text-yellow-400' }
    if (['ts', 'tsx'].includes(ext)) return { icon: FileCode2, color: 'text-blue-400' }
    if (['py'].includes(ext)) return { icon: FileCode2, color: 'text-green-400' }
    if (['vue'].includes(ext)) return { icon: FileCode2, color: 'text-emerald-400' }
    if (['html', 'htm'].includes(ext)) return { icon: FileCode2, color: 'text-orange-400' }
    if (['css', 'scss', 'less'].includes(ext)) return { icon: FileCode2, color: 'text-purple-400' }
    if (['go'].includes(ext)) return { icon: FileCode2, color: 'text-cyan-400' }
    if (['rs'].includes(ext)) return { icon: FileCode2, color: 'text-orange-500' }
    if (['java', 'kt'].includes(ext)) return { icon: FileCode2, color: 'text-red-400' }
    if (['rb'].includes(ext)) return { icon: FileCode2, color: 'text-red-500' }
    if (['php'].includes(ext)) return { icon: FileCode2, color: 'text-blue-400' }
    if (['c', 'cpp', 'h', 'hpp'].includes(ext)) return { icon: FileCode2, color: 'text-blue-500' }
    if (['sh', 'bash', 'zsh'].includes(ext)) return { icon: FileCode2, color: 'text-green-500' }
    if (['sql'].includes(ext)) return { icon: FileCode2, color: 'text-amber-400' }

    // Config/Data files
    if (['json'].includes(ext)) return { icon: Braces, color: 'text-yellow-500' }
    if (['yaml', 'yml'].includes(ext)) return { icon: FileCog, color: 'text-pink-400' }
    if (['xml'].includes(ext)) return { icon: FileCode2, color: 'text-orange-300' }
    if (['toml', 'ini', 'env', 'conf', 'cfg'].includes(ext)) return { icon: FileCog, color: 'text-gray-400' }

    // Documents
    if (['pdf'].includes(ext)) return { icon: FileText, color: 'text-red-400' }
    if (['docx', 'doc'].includes(ext)) return { icon: FileText, color: 'text-blue-500' }
    if (['md', 'mdx'].includes(ext)) return { icon: FileText, color: 'text-sky-400' }
    if (['txt'].includes(ext)) return { icon: FileText, color: 'text-gray-400' }

    // Spreadsheets
    if (['xlsx', 'xls', 'csv', 'tsv'].includes(ext)) return { icon: FileSpreadsheet, color: 'text-emerald-500' }

    // Images
    if (IMAGE_EXTENSIONS.includes(ext)) return { icon: FileImage, color: 'text-sky-400' }

    // Archives
    if (['zip', 'tar', 'gz', 'rar', '7z', 'bz2'].includes(ext)) return { icon: FileArchive, color: 'text-amber-500' }

    // Audio
    if (['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'].includes(ext)) return { icon: FileAudio, color: 'text-pink-500' }

    // Video
    if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv'].includes(ext)) return { icon: FileVideo, color: 'text-rose-500' }

    // Fonts
    if (['ttf', 'otf', 'woff', 'woff2', 'eot'].includes(ext)) return { icon: FileType, color: 'text-slate-500' }

    // Default
    return { icon: FileIcon, color: 'text-zinc-500' }
}

/**
 * Composable for file type detection and icon configuration
 */
export function useFileDetection(item) {
    const extension = computed(() => {
        if (item.value?.is_dir) return ''
        return getExtension(item.value?.name)
    })

    const fileIconConfig = computed(() => {
        if (item.value?.is_dir) return null
        return getFileIconConfig(item.value?.name)
    })

    const isImage = computed(() => {
        return isImageFile(item.value?.name)
    })

    return {
        extension,
        fileIconConfig,
        isImage
    }
}

// Export utilities for use without the full composable
export {
    IMAGE_EXTENSIONS,
    DOCUMENT_EXTENSIONS,
    ALL_FILE_EXTENSIONS,
    getExtension,
    isImageFile,
    getFileName,
    getFileIconConfig
}
