export function createInitialState(config) {
  return {
    messages: [],
    userInput: '',
    isLoading: false,
    activeNav: 'newChat',
    abortController: null,
    sessionId: `session_${Date.now()}`,
    sessions: [],
    showHistorySidebar: false,
    isComposing: false,
    documents: [],
    documentsLoading: false,
    selectedFile: null,
    isUploading: false,
    uploadProgress: '',
    token: localStorage.getItem(config.TOKEN_STORAGE_KEY) || '',
    currentUser: null,
    authMode: 'login',
    authForm: {
      username: '',
      password: '',
      role: 'user',
      admin_code: ''
    },
    authLoading: false,
    isDarkMode: localStorage.getItem(config.THEME_STORAGE_KEY) === 'dark'
  };
}
