import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Github, Notebook, CheckCircle, XCircle, ExternalLink, Loader2, RefreshCw, Key, Unplug } from 'lucide-react';
import { connectIntegration, getIntegrations, IntegrationStatus, getGitHubRepos, getOneNotePages, disconnectIntegration } from '../api';

const INTEGRATIONS = [
    {
        id: 'github',
        name: 'GitHub',
        icon: Github,
        color: 'text-gray-200',
        bgColor: 'bg-gray-800',
        description: 'Connect to view your repositories.',
        helpText: "Generate a Personal Access Token (Classic) with 'repo' scope from your GitHub Developer Settings.",
        link: "https://github.com/settings/tokens"
    },
    {
        id: 'onenote',
        name: 'OneNote',
        icon: Notebook,
        color: 'text-purple-400',
        bgColor: 'bg-purple-900/20',
        description: 'Access your recent notes and pages.',
        helpText: "You need an OAuth Access Token for Microsoft Graph API (scope: 'Notes.Read'). Use Graph Explorer for testing.",
        link: "https://developer.microsoft.com/en-us/graph/graph-explorer"
    }
];

export function IntegrationDashboard() {
    const [statuses, setStatuses] = useState<Record<string, IntegrationStatus>>({});
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState<string | null>(null);
    const [disconnecting, setDisconnecting] = useState<string | null>(null);
    const [tokens, setTokens] = useState<Record<string, string>>({});

    // Data check states
    const [repos, setRepos] = useState<any[] | null>(null);
    const [notes, setNotes] = useState<any[] | null>(null);
    const [loadingData, setLoadingData] = useState<string | null>(null);

    useEffect(() => {
        loadIntegrations();
    }, []);

    const loadIntegrations = async () => {
        try {
            const data = await getIntegrations();
            const map: Record<string, IntegrationStatus> = {};
            data.forEach((s: IntegrationStatus) => map[s.provider] = s);
            setStatuses(map);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async (providerId: string) => {
        const token = tokens[providerId];
        if (!token) return;

        setConnecting(providerId);
        try {
            await connectIntegration(providerId, token);
            await loadIntegrations();
            setTokens(prev => ({ ...prev, [providerId]: '' })); // Clear input
        } catch (e) {
            console.error("Connection failed", e);
            alert("Failed to connect. Check your token.");
        } finally {
            setConnecting(null);
        }
    };

    const handleFetchData = async (providerId: string) => {
        setLoadingData(providerId);
        try {
            if (providerId === 'github') {
                const data = await getGitHubRepos();
                setRepos(data);
            } else if (providerId === 'onenote') {
                const data = await getOneNotePages();
                setNotes(data);
            }
        } catch (e) {
            console.error(e);
            alert("Failed to fetch data. Token might be expired.");
        } finally {
            setLoadingData(null);
        }
    };

    const handleDisconnect = async (providerId: string, providerName: string) => {
        const confirmed = window.confirm(
            `Are you sure you want to disconnect ${providerName}? This will remove the integration and you'll need to reconnect to use it again.`
        );
        
        if (!confirmed) return;

        setDisconnecting(providerId);
        try {
            await disconnectIntegration(providerId);
            await loadIntegrations();
            // Clear the data preview if it was showing
            if (providerId === 'github') setRepos(null);
            if (providerId === 'onenote') setNotes(null);
        } catch (e) {
            console.error("Disconnect failed", e);
            alert("Failed to disconnect. Please try again.");
        } finally {
            setDisconnecting(null);
        }
    };

    if (loading) {
        return <div className="flex justify-center p-12"><Loader2 className="animate-spin w-8 h-8 text-primary" /></div>;
    }

    return (
        <div className="p-6 space-y-8 animate-in fade-in duration-500">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h2 className="text-3xl font-bold text-text mb-2">Integrations</h2>
                    <p className="text-muted">Connect your favorite tools to import data into Lumina.</p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {INTEGRATIONS.map((tool) => {
                    const status = statuses[tool.id];
                    const isConnected = status?.is_connected;
                    const Icon = tool.icon;

                    return (
                        <div key={tool.id} className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm flex flex-col">
                            <div className={`p-6 ${tool.bgColor} bg-opacity-30 border-b border-border/50 flex items-center justify-between`}>
                                <div className="flex items-center gap-4">
                                    <div className={`p-3 rounded-lg ${tool.bgColor} bg-opacity-70 ring-1 ring-white/10`}>
                                        <Icon className={`w-6 h-6 ${tool.color}`} />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-lg text-text">{tool.name}</h3>
                                        <div className="flex items-center gap-2 mt-1">
                                            {isConnected ? (
                                                <span className="flex items-center gap-1.5 text-xs font-medium text-green-500 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                                                    <CheckCircle className="w-3 h-3" /> Connected
                                                </span>
                                            ) : (
                                                <span className="flex items-center gap-1.5 text-xs font-medium text-muted bg-input px-2 py-0.5 rounded-full border border-border">
                                                    <XCircle className="w-3 h-3" /> Not Connected
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                {isConnected && (
                                    <button
                                        onClick={() => handleFetchData(tool.id)}
                                        disabled={loadingData === tool.id}
                                        className="p-2 hover:bg-white/10 rounded-full transition-colors text-muted hover:text-text"
                                        title="Test Connection & Fetch Data"
                                    >
                                        <RefreshCw className={`w-5 h-5 ${loadingData === tool.id ? 'animate-spin' : ''}`} />
                                    </button>
                                )}
                            </div>

                            <div className="p-6 flex-1 flex flex-col gap-4">
                                <p className="text-sm text-text/80">{tool.description}</p>

                                {!isConnected ? (
                                    <div className="space-y-4 mt-auto">
                                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs text-blue-200">
                                            <p className="mb-2 font-medium">How to connect:</p>
                                            <p className="opacity-80 leading-relaxed">{tool.helpText}</p>
                                            <a
                                                href={tool.link}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="inline-flex items-center gap-1 mt-2 text-blue-400 hover:text-blue-300 font-bold hover:underline"
                                            >
                                                Get Token <ExternalLink className="w-3 h-3" />
                                            </a>
                                        </div>

                                        <div className="flex gap-2">
                                            <div className="relative flex-1">
                                                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                                                <input
                                                    type="password"
                                                    placeholder="Paste Access Token"
                                                    value={tokens[tool.id] || ''}
                                                    onChange={e => setTokens(prev => ({ ...prev, [tool.id]: e.target.value }))}
                                                    className="w-full bg-input border border-border rounded-lg py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all placeholder:text-muted/50"
                                                />
                                            </div>
                                            <button
                                                onClick={() => handleConnect(tool.id)}
                                                disabled={!tokens[tool.id] || connecting === tool.id}
                                                className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                                            >
                                                {connecting === tool.id ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save'}
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="mt-auto">
                                        <div className="text-center py-6 bg-green-500/5 rounded-lg border border-green-500/10 border-dashed">
                                            <p className="text-green-500 text-sm font-medium">Integration Active</p>
                                            <p className="text-xs text-muted mt-1">Lumina can now access your {tool.name} data.</p>
                                        </div>
                                        <button
                                            onClick={() => handleDisconnect(tool.id, tool.name)}
                                            disabled={disconnecting === tool.id}
                                            className="w-full mt-4 flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 px-4 py-2 rounded-lg text-sm font-medium transition-all border border-red-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {disconnecting === tool.id ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    Disconnecting...
                                                </>
                                            ) : (
                                                <>
                                                    <Unplug className="w-4 h-4" />
                                                    Disconnect
                                                </>
                                            )}
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Data Preview Section (For testing/demo) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
                {repos && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                        <h3 className="text-xl font-bold text-text flex items-center gap-2">
                            <Github className="w-5 h-5" /> Your Repositories
                        </h3>
                        <div className="bg-surface border border-border rounded-xl overflow-hidden max-h-96 overflow-y-auto custom-scrollbar">
                            {repos.length === 0 ? (
                                <div className="p-8 text-center text-muted">No repositories found.</div>
                            ) : (
                                <div className="divide-y divide-border">
                                    {repos.map((repo: any) => (
                                        <div key={repo.id} className="p-4 hover:bg-input/50 transition-colors">
                                            <a href={repo.html_url} target="_blank" rel="noreferrer" className="text-base font-semibold text-primary hover:underline block truncate">
                                                {repo.name}
                                            </a>
                                            <p className="text-sm text-muted mt-1 line-clamp-2">{repo.description || 'No description'}</p>
                                            <div className="flex items-center gap-2 mt-2 text-xs text-secondary font-medium">
                                                <span>⭐ {repo.stars} Stars</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}

                {notes && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                        <h3 className="text-xl font-bold text-text flex items-center gap-2">
                            <Notebook className="w-5 h-5 text-purple-400" /> Recent Notes
                        </h3>
                        <div className="bg-surface border border-border rounded-xl overflow-hidden max-h-96 overflow-y-auto custom-scrollbar">
                            {notes.length === 0 ? (
                                <div className="p-8 text-center text-muted">No pages found.</div>
                            ) : (
                                <div className="divide-y divide-border">
                                    {notes.map((page: any) => (
                                        <div key={page.id} className="p-4 hover:bg-input/50 transition-colors">
                                            <h4 className="text-base font-semibold text-purple-300 block truncate">
                                                {page.title}
                                            </h4>
                                            {page.links?.oneNoteWebUrl && (
                                                <a
                                                    href={page.links.oneNoteWebUrl.href}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="inline-flex items-center gap-1 mt-2 text-xs text-muted hover:text-text transition-colors border border-border rounded-full px-3 py-1"
                                                >
                                                    Open in OneNote <ExternalLink className="w-3 h-3" />
                                                </a>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
