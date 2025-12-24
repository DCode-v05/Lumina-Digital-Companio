import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Coins, Gift, Lock, ShoppingBag, Coffee, Heart, Music, Gamepad2, BookOpen, Sun, Moon, Smartphone, Clock, Youtube, Tv, Trophy, Star, Zap, User, History as HistoryIcon, X } from 'lucide-react';
import { getRewards, redeemReward } from '../api';

const ICONS: Record<string, any> = {
    coffee: Coffee,
    heart: Heart,
    music: Music,
    shopping: ShoppingBag,
    game: Gamepad2,
    book: BookOpen,
    sun: Sun,
    moon: Moon,
    smartphone: Smartphone,
    clock: Clock,
    youtube: Youtube,
    tv: Tv,
    trophy: Trophy,
    star: Star,
    zap: Zap,
    user: User,
    default: Gift
};

export function RewardDashboard({ favorites }: { favorites?: string }) {
    const [balance, setBalance] = useState(0);
    const [items, setItems] = useState<any[]>([]);
    const [history, setHistory] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [redeeming, setRedeeming] = useState<string | null>(null);
    const [showHistory, setShowHistory] = useState(false);

    useEffect(() => {
        setLoading(true);
        loadRewards();
    }, [favorites]); // Reload when favorites change

    const loadRewards = async () => {
        try {
            const data = await getRewards();
            setBalance(data.coins);
            setItems(data.items);
            setHistory(data.history || []);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleRedeem = async (id: string, cost: number) => {
        if (balance < cost) return;
        setRedeeming(id);
        try {
            const res = await redeemReward(cost);
            setBalance(res.new_balance);
            // Add local history item optimistically or reload
            setHistory(prev => [...prev, { date: new Date().toISOString().split('T')[0], description: "Reward Redeemed", amount: -cost }]);
            alert("Reward Redeemed! Enjoy your break.");
        } catch (e) {
            alert("Redemption failed");
        } finally {
            setRedeeming(null);
        }
    }

    const categories = Array.from(new Set(items.map(i => i.category || 'General')));

    if (loading) return <div className="p-8 text-center text-muted animate-pulse">Loading Rewards Store...</div>;

    return (
        <div className="space-y-8 pb-12 relative">
            {/* Header / Stats */}
            <div className="bg-gradient-to-r from-amber-500/10 to-orange-600/10 border border-amber-500/20 rounded-2xl p-4 flex items-center justify-between shadow-lg relative overflow-hidden">
                <div className="absolute inset-0 bg-grid-white/5 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.6))] pointer-events-none"></div>
                <div className="relative z-10">
                    <h2 className="text-xl font-bold text-amber-100">My Reward Store</h2>
                    <p className="text-sm text-amber-200/60">Balance work with awards.</p>
                </div>
                <div className="flex flex-col items-end relative z-10 gap-2">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => setShowHistory(true)}
                            className="text-amber-200/60 hover:text-amber-100 transition-colors p-1"
                            title="Transaction History"
                        >
                            <HistoryIcon className="w-5 h-5" />
                        </button>
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold text-amber-500 uppercase tracking-widest">Available</span>
                            <div className="text-3xl font-black text-amber-400 flex items-center gap-2 drop-shadow-sm">
                                <Coins className="w-6 h-6 fill-amber-400/20 stroke-[3px]" />
                                {balance}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Reward Grid */}
            <div className="space-y-12">
                {categories.map((cat) => {
                    const catItems = items.filter(i => (i.category || 'General') === cat);
                    return (
                        <div key={cat} className="space-y-4">
                            <h3 className="text-xl font-bold text-muted flex items-center gap-2 border-l-4 border-primary/40 pl-3">
                                {cat} Rewards
                            </h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                                {catItems.map((item, idx) => {
                                    const Icon = ICONS[item.icon] || ICONS[item.icon?.split('-')[0]] || ICONS.default;
                                    const canAfford = balance >= item.cost;

                                    return (
                                        <motion.div
                                            key={item.id}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            transition={{ delay: idx * 0.02 }}
                                            className={`relative group bg-surface border border-border/50 rounded-xl p-5 hover:border-primary/30 transition-all hover:shadow-xl flex flex-col justify-between h-48 ${!canAfford ? 'opacity-60 grayscale-[0.5]' : ''}`}
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl bg-gradient-to-br ${canAfford ? 'from-primary/20 to-secondary/20 text-primary' : 'from-gray-500/10 to-gray-600/10 text-muted'}`}>
                                                    <Icon className="w-5 h-5" />
                                                </div>
                                                <span className={`text-sm font-bold px-2 py-1 rounded-md flex items-center gap-1 ${canAfford ? 'bg-amber-500/10 text-amber-500' : 'bg-input text-muted'}`}>
                                                    {item.cost} <Coins className="w-3 h-3" />
                                                </span>
                                            </div>

                                            <div>
                                                <h4 className="font-bold text-text line-clamp-2 leading-tight mb-1 group-hover:text-primary transition-colors">{item.name}</h4>
                                            </div>

                                            <button
                                                onClick={() => handleRedeem(item.id, item.cost)}
                                                disabled={!canAfford || redeeming === item.id}
                                                className={`mt-4 w-full py-2 rounded-lg text-xs font-bold uppercase tracking-wide transition-all flex items-center justify-center gap-2
                                                    ${canAfford
                                                        ? 'bg-text text-background hover:bg-primary hover:text-white hover:scale-[1.02] shadow-lg'
                                                        : 'bg-input text-muted cursor-not-allowed border border-border'
                                                    }
                                                `}
                                            >
                                                {redeeming === item.id ? (
                                                    <span className="animate-pulse">Processing...</span>
                                                ) : !canAfford ? (
                                                    <><Lock className="w-3 h-3" /> Locked</>
                                                ) : (
                                                    <>Redeem</>
                                                )}
                                            </button>
                                        </motion.div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* History Modal */}
            <AnimatePresence>
                {showHistory && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={() => setShowHistory(false)}>
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="bg-surface border border-border w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="p-4 border-b border-border flex justify-between items-center bg-input/20">
                                <h3 className="font-bold text-lg flex items-center gap-2">
                                    <HistoryIcon className="w-5 h-5 text-primary" /> Coin History
                                </h3>
                                <button onClick={() => setShowHistory(false)} className="p-1 hover:bg-input rounded-full text-muted hover:text-text transition-colors">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>

                            <div className="overflow-y-auto p-4 space-y-3">
                                {history.length === 0 ? (
                                    <div className="text-center py-8 text-muted">
                                        <p>No transactions yet.</p>
                                    </div>
                                ) : (
                                    [...history].reverse().map((txn, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-input/30 border border-border/50">
                                            <div>
                                                <p className="text-sm font-medium text-text">{txn.description}</p>
                                                <p className="text-xs text-muted">{txn.date}</p>
                                            </div>
                                            <div className={`text-sm font-bold ${txn.amount > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {txn.amount > 0 ? '+' : ''}{txn.amount}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
