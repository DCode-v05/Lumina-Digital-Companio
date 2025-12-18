import { useState, useEffect, useRef } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Trash2, PlusCircle, MessageSquare, Send, User, Bot, Loader2, Sparkles, LogOut, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';
import { sendMessage, getHistory, getMe, getChats, createChat, deleteChat, ChatSession, getProfile } from './api';
import './index.css';

import Login from './pages/Login';
import Register from './pages/Register';
import { ThemeToggle } from './components/ThemeToggle';

interface Message {
    role: 'user' | 'model';
    content: string;
}


// Simple Toast Component
function Toast({ message, onClose }: { message: string, onClose: () => void }) {
    useEffect(() => {
        const timer = setTimeout(onClose, 3000);
        return () => clearTimeout(timer);
    }, [onClose]);

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: -20, x: '-50%' }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="fixed top-6 left-1/2 -translate-x-1/2 z-50 bg-green-500/90 backdrop-blur text-white px-6 py-3 rounded-full shadow-xl flex items-center gap-3 font-medium text-sm"
            >
                <Sparkles className="w-4 h-4" />
                <span>{message}</span>
            </motion.div>
        </AnimatePresence>
    );
}

// Profile Memory Modal
function ProfileModal({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const [facts, setFacts] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            loadProfile();
        }
    }, [isOpen]);

    const loadProfile = async () => {
        setLoading(true);
        try {
            const data = await getProfile();
            setFacts(data.facts);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="bg-surface border border-border w-full max-w-md rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
                    onClick={e => e.stopPropagation()}
                >
                    <div className="p-6 border-b border-border">
                        <div className="flex items-center gap-3 mb-1">
                            <div className="p-2 bg-primary/10 rounded-lg text-primary">
                                <User className="w-5 h-5" />
                            </div>
                            <h3 className="text-lg font-semibold text-text">Memory & Personalization</h3>
                        </div>
                        <p className="text-sm text-muted">What Lumina has learned about you to provide better assistance.</p>
                    </div>

                    <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center py-8 text-muted">
                                <Loader2 className="w-8 h-8 animate-spin mb-2" />
                                <p className="text-sm">Accessing memory banks...</p>
                            </div>
                        ) : facts.length > 0 ? (
                            <ul className="space-y-3">
                                {facts.map((fact, index) => (
                                    <motion.li
                                        key={index}
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="flex gap-3 text-sm text-text bg-input/50 p-3 rounded-lg border border-border/50"
                                    >
                                        <div className="w-1.5 h-1.5 rounded-full bg-secondary mt-1.5 flex-shrink-0" />
                                        <span>{fact}</span>
                                    </motion.li>
                                ))}
                            </ul>
                        ) : (
                            <div className="text-center py-8 text-muted">
                                <p>Lumina hasn't learned any specific facts about you yet.</p>
                                <p className="text-xs mt-2">Chat more to build your personalized profile!</p>
                            </div>
                        )}
                    </div>

                    <div className="bg-input/30 px-6 py-4 flex justify-end border-t border-border">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-text hover:bg-input rounded-lg transition-colors"
                        >
                            Close
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

// Confirmation Modal Component
function ConfirmationModal({ isOpen, onClose, onConfirm, title, message }: { isOpen: boolean, onClose: () => void, onConfirm: () => void, title: string, message: string }) {
    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.95, opacity: 0 }}
                    className="bg-surface border border-border w-full max-w-sm rounded-xl shadow-2xl overflow-hidden"
                    onClick={e => e.stopPropagation()}
                >
                    <div className="p-6">
                        <h3 className="text-lg font-semibold text-text mb-2">{title}</h3>
                        <p className="text-sm text-muted">{message}</p>
                    </div>
                    <div className="bg-input/50 px-6 py-4 flex justify-end gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-text hover:bg-input rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => {
                                onConfirm();
                                onClose();
                            }}
                            className="px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors"
                        >
                            Delete
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}

function ProtectedRoute({ children }: { children: JSX.Element }) {
    const token = localStorage.getItem('token');
    if (!token) {
        return <Navigate to="/login" replace />;
    }
    return children;
}

function ChatInterface() {
    const [input, setInput] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [chats, setChats] = useState<ChatSession[]>([]);
    const [currentChatId, setCurrentChatId] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [userData, setUserData] = useState<{ full_name: string } | null>(null);
    const [showSuccessToast, setShowSuccessToast] = useState(false);
    const [deleteId, setDeleteId] = useState<string | null>(null); // State for modal
    const [showProfileModal, setShowProfileModal] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const navigate = useNavigate();

    // Check for login success flag
    useEffect(() => {
        const justLoggedIn = localStorage.getItem('loginSuccess');
        if (justLoggedIn) {
            setShowSuccessToast(true);
            localStorage.removeItem('loginSuccess');
        }
    }, []);

    // Auto-focus input when loading finishes (bot replies)
    useEffect(() => {
        if (!loading) {
            // Tiny timeout to ensure DOM is ready and state is settled
            setTimeout(() => {
                inputRef.current?.focus();
            }, 50);
        }
    }, [loading]);

    useEffect(() => {
        const init = async () => {
            try {
                const user = await getMe();
                setUserData(user);

                const userChats = await getChats();
                setChats(userChats);

                // Default to New Chat instead of opening last chat
                handleNewChat();

            } catch (err) {
                // Only redirect if unauthorized
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                if ((err as any).response?.status === 401) {
                    localStorage.removeItem('token');
                    navigate('/login');
                }
            }
        };
        init();
    }, [navigate]);

    const selectChat = async (id: string | null) => {
        if (!id) return;
        setCurrentChatId(id);
        setMessages([]); // Clear previous view
        try {
            const history = await getHistory(id);
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const mapped = history.map((h: any) => ({
                role: h.role,
                content: h.parts[0]
            }));
            setMessages(mapped);
        } catch (e) {
            console.error("Failed to load chat", e);
        }
    }

    const handleNewChat = () => {
        setCurrentChatId(null);
        setMessages([]);
    }

    const handleDeleteClick = (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        setDeleteId(id);
    }

    const confirmDeleteChat = async () => {
        if (!deleteId) return;
        const id = deleteId;
        setDeleteId(null);

        try {
            await deleteChat(id);
            const updated = chats.filter(c => c.id !== id);
            setChats(updated);

            if (currentChatId === id) {
                if (updated.length > 0) {
                    selectChat(updated[0].id);
                } else {
                    handleNewChat();
                }
            }
        } catch (e) {
            console.error(e);
        }
    }

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            if (!currentChatId) {
                // Should ideally not happen if handled correctly, but safety net
                const newChat = await createChat();
                setCurrentChatId(newChat.id);
                // We don't wait for state update to be reliable immediately in same scope usually, 
                // but let's assume valid ID for API call
                const data = await sendMessage(newChat.id, userMsg);
                setMessages(prev => [...prev, { role: 'model', content: data.response }]);

                // Update chat title if backend returned one
                if (data.title) {
                    newChat.title = data.title;
                }
                setChats([newChat, ...chats]); // Update list
            } else {
                const data = await sendMessage(currentChatId, userMsg);
                setMessages(prev => [...prev, { role: 'model', content: data.response }]);
            }
        } catch (error) {
            console.error(error);
            setMessages(prev => [...prev, { role: 'model', content: "Error: Could not reach the AI companion." }]);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        }
    };

    const handleInputResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = `${e.target.scrollHeight}px`;
    }

    return (
        <div className="flex h-screen w-full bg-background text-text font-sans overflow-hidden">
            {showSuccessToast && <Toast message="Welcome back! Ready to learn?" onClose={() => setShowSuccessToast(false)} />}

            <ConfirmationModal
                isOpen={!!deleteId}
                onClose={() => setDeleteId(null)}
                onConfirm={confirmDeleteChat}
                title="Delete Chat"
                message="Are you sure you want to delete this conversation? This action cannot be undone."
            />

            <ProfileModal
                isOpen={showProfileModal}
                onClose={() => setShowProfileModal(false)}
            />

            {/* Sidebar */}
            <AnimatePresence mode="wait">
                {sidebarOpen && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 280, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        className="flex flex-col border-r border-border dark:border-white/5 bg-surface relative z-20"
                    >
                        <div className="p-4 flex items-center justify-between border-b border-border dark:border-white/5">
                            <div className="flex items-center gap-2 text-primary font-bold text-xl">
                                <Sparkles className="w-6 h-6" />
                                <span>Lumina</span>
                            </div>
                            <button onClick={() => setSidebarOpen(false)} className="md:hidden p-1 text-muted hover:text-text">
                                <PanelLeftClose />
                            </button>
                        </div>

                        <div className="px-3 pb-2 pt-4">
                            <button
                                onClick={handleNewChat}
                                className="w-full flex items-center gap-2 p-3 rounded-lg bg-primary hover:bg-blue-600 text-white transition-all shadow-md active:scale-95"
                            >
                                <PlusCircle className="w-4 h-4" />
                                <span>New Chat</span>
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
                            <div className="text-xs text-muted uppercase tracking-wider font-semibold mb-2 px-2">Recent Chats</div>
                            {chats.map(chat => (
                                <div
                                    key={chat.id}
                                    onClick={() => selectChat(chat.id)}
                                    className={`group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-all ${currentChatId === chat.id
                                        ? 'bg-primary/10 text-primary '
                                        : 'hover:bg-input text-muted hover:text-text '
                                        }`}
                                >
                                    <div className="flex items-center gap-3 truncate">
                                        <MessageSquare className="w-4 h-4 flex-shrink-0" />
                                        <span className="truncate text-sm">{chat.title || 'Untitled Chat'}</span>
                                    </div>
                                    <button
                                        onClick={(e) => handleDeleteClick(e, chat.id)}
                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 hover:text-red-500 rounded transition-all"
                                    >
                                        <Trash2 className="w-3 h-3" />
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 border-t border-border dark:border-white/5 mt-auto">
                            <button
                                onClick={() => setShowProfileModal(true)}
                                className="w-full flex items-center gap-3 mb-2 px-2 py-2 rounded-lg hover:bg-input transition-colors text-left group"
                            >
                                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary to-secondary flex items-center justify-center text-white font-bold text-xs ring-2 ring-background group-hover:ring-offset-2 transition-all">
                                    {userData?.full_name?.charAt(0) || 'U'}
                                </div>
                                <div className="flex-1 overflow-hidden">
                                    <p className="text-sm font-medium truncate text-text">{userData?.full_name}</p>
                                    <p className="text-xs text-muted truncate">View Memory</p>
                                </div>
                            </button>
                            <button onClick={handleLogout} className="w-full flex items-center gap-3 p-2 rounded-lg hover:bg-red-500/10 hover:text-red-400 transition-colors text-sm text-left text-muted">
                                <LogOut className="w-4 h-4" />
                                <span>Sign Out</span>
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Chat Area */}
            <div className="flex-1 flex flex-col relative bg-background h-screen">
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-5 pointer-events-none mix-blend-overlay"></div>

                {/* Header */}
                <header className="h-16 border-b border-border/60 dark:border-white/5 flex items-center justify-between px-6 bg-surface/80 backdrop-blur-2xl sticky top-0 z-10 transition-colors shadow-sm">
                    <div className="flex items-center gap-3">
                        {!sidebarOpen && (
                            <button onClick={() => setSidebarOpen(true)} className="p-2 hover:bg-input rounded-lg">
                                <PanelLeftOpen className="w-5 h-5 text-muted" />
                            </button>
                        )}
                        <h1 className="text-lg font-medium text-text">
                            {chats.find(c => c.id === currentChatId)?.title || 'Study Companion'}
                        </h1>
                    </div>
                    <div>
                        <ThemeToggle />
                    </div>
                </header>

                {/* Chat Stream */}
                <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth">
                    <AnimatePresence>
                        {messages.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center text-muted opacity-50">
                                <Sparkles className="w-12 h-12 mb-4" />
                                <p>Start a conversation to begin learning.</p>
                            </div>
                        )}
                        {messages.map((msg, idx) => (
                            <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                {msg.role === 'model' && (
                                    <div className="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center flex-shrink-0 border border-secondary/20 shadow-sm mt-1">
                                        <Bot className="w-4 h-4 text-secondary" />
                                    </div>
                                )}

                                <div
                                    className={`max-w-[80%] md:max-w-[70%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-sm transition-colors ${msg.role === 'user'
                                        ? 'bg-primary text-white rounded-br-none'
                                        : 'bg-surface text-text rounded-bl-none' /* Removed border border-border */
                                        }`}
                                >
                                    <ReactMarkdown className="prose dark:prose-invert prose-sm md:prose-base max-w-none">
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>

                                {msg.role === 'user' && (
                                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 border border-primary/20 shadow-sm mt-1">
                                        <User className="w-4 h-4 text-primary" />
                                    </div>
                                )}
                            </motion.div>
                        ))}
                    </AnimatePresence>

                    {loading && (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4">
                            <div className="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center border border-secondary/20 shadow-sm">
                                <Bot className="w-4 h-4 text-secondary" />
                            </div>
                            <div className="bg-surface rounded-2xl rounded-bl-none px-6 py-4 shadow-sm flex items-center gap-3">
                                <span className="text-sm text-foreground/80 font-medium">Lumina is thinking</span>
                                <div className="flex space-x-1">
                                    <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                    <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                    <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce"></span>
                                </div>
                            </div>
                        </motion.div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 md:p-6 bg-gradient-to-t from-background via-background to-transparent transition-colors">
                    <div className="max-w-4xl mx-auto relative group">
                        <div className="absolute -inset-1 bg-gradient-to-r from-primary/50 to-secondary/50 rounded-xl opacity-10 group-hover:opacity-20 transition blur-lg"></div>
                        <div className="relative flex items-center bg-white dark:bg-zinc-800 rounded-xl border border-zinc-200 dark:border-none shadow-xl transition-all">
                            <textarea
                                ref={inputRef as any}
                                value={input}
                                autoFocus
                                onChange={handleInputResize}
                                onKeyDown={handleKeyDown}
                                placeholder="Ask anything about your studies..."
                                className="flex-1 bg-transparent px-6 py-4 outline-none text-text placeholder-muted resize-none max-h-48 overflow-y-auto"
                                disabled={loading}
                                rows={1}
                            />
                            <button
                                onClick={handleSend}
                                disabled={loading || !input.trim()}
                                className="p-3 mr-2 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                            </button>
                        </div>
                        <div className="text-center mt-2 text-xs text-muted">
                            Lumina can make mistakes. Verify important information.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <ChatInterface />
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
