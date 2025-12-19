import axios from 'axios';

const API_URL = 'http://localhost:8000';

axios.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

axios.interceptors.response.use(
    (response) => response,
    (error) => {
        // Prevent redirect loop if we are already on login or register page
        // and allow the component to handle the specific 401 error message.
        if (error.response?.status === 401) {
            const currentPath = window.location.pathname;
            if (currentPath !== '/login' && currentPath !== '/register') {
                localStorage.removeItem('token');
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

export interface ChatMessage {
    role: 'user' | 'model';
    parts: string[];
}

export interface ChatSession {
    id: string;
    title: string;
    created_at: number;
}

// --- Auth ---

export const login = async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await axios.post(`${API_URL}/token`, formData);
    return response.data;
}

export const register = async (email: string, password: string, fullName: string) => {
    const response = await axios.post(`${API_URL}/register`, {
        email,
        password,
        full_name: fullName
    });
    return response.data;
}

export const getMe = async () => {
    const response = await axios.get(`${API_URL}/users/me`);
    return response.data;
}

export const getProfile = async () => {
    const response = await axios.get(`${API_URL}/users/me/profile`);
    return response.data; // { profile_text: string, facts: string[] }
}

export const updateProfile = async (profileText: string) => {
    const response = await axios.put(`${API_URL}/users/me/profile`, { profile_text: profileText });
    return response.data;
}

// --- Chat Management ---

export const createChat = async (title: string = "New Chat") => {
    const response = await axios.post(`${API_URL}/chats`, { title });
    return response.data; // { id, title, created_at }
}

export const getChats = async () => {
    const response = await axios.get(`${API_URL}/chats`);
    return response.data; // [ { id, ... }, ... ]
}

export const deleteChat = async (chatId: string) => {
    const response = await axios.delete(`${API_URL}/chats/${chatId}`);
    return response.data;
}

// --- Messaging ---

export const sendMessage = async (chatId: string, message: string) => {
    const response = await axios.post(`${API_URL}/chat`, {
        chat_id: chatId,
        message: message
    });
    return response.data; // { response: string, chat_id: string, title?: string, mode: string }
};

export const getHistory = async (chatId: string) => {
    const response = await axios.get(`${API_URL}/chats/${chatId}/history`);
    return response.data;
};
