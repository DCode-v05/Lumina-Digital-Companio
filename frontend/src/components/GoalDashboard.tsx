import { useState, useEffect } from 'react';
import { Target, CheckCircle2, Circle, CalendarCheck, Trash2, Clock, ChevronDown, ChevronUp, Loader2, Plus, Edit2, X, AlertTriangle, RefreshCw, BrainCircuit } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Goal, getGoals, createGoal, updateGoal, deleteGoal, decomposeGoal, getGoalQuiz } from '../api';

export function GoalDashboard() {
    const [goals, setGoals] = useState<Goal[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandingId, setExpandingId] = useState<number | null>(null);
    const [processingId, setProcessingId] = useState<number | null>(null);

    // Modal States
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingGoal, setEditingGoal] = useState<Partial<Goal> | null>(null);
    const [deleteId, setDeleteId] = useState<number | null>(null);

    // Quiz States
    const [isQuizOpen, setIsQuizOpen] = useState(false);
    const [quizData, setQuizData] = useState<any>(null);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [score, setScore] = useState(0);
    const [showResults, setShowResults] = useState(false);
    const [loadingQuiz, setLoadingQuiz] = useState(false);

    useEffect(() => {
        loadGoals();
    }, []);

    const loadGoals = async () => {
        try {
            const data = await getGoals();
            setGoals(data);
        } catch (e) {
            console.error("Failed to load goals", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSaveGoal = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingGoal || !editingGoal.title) return;

        try {
            if (editingGoal.id) {
                // Update
                const updated = await updateGoal(editingGoal.id, editingGoal);
                setGoals(prev => prev.map(g => g.id === updated.id ? updated : g));
            } else {
                // Create
                // @ts-ignore - Backend handles defaults
                const newGoal = await createGoal({
                    title: editingGoal.title,
                    description: editingGoal.description || "",
                    duration: editingGoal.duration || 7,
                    duration_unit: editingGoal.duration_unit || "days",
                    priority: editingGoal.priority || "Medium",
                    subtasks: "[]"
                });
                setGoals(prev => [newGoal, ...prev]);
            }
            setIsEditModalOpen(false);
            setEditingGoal(null);
        } catch (error) {
            console.error("Failed to save goal", error);
        }
    };

    const confirmDelete = async () => {
        if (!deleteId) return;
        try {
            await deleteGoal(deleteId);
            setGoals(prev => prev.filter(g => g.id !== deleteId));
            setDeleteId(null);
        } catch (e) {
            console.error("Failed to delete", e);
        }
    };

    // State for breakdown modal
    const [breakdownGoalId, setBreakdownGoalId] = useState<number | null>(null);

    const handleDecomposeClick = (goal: Goal) => {
        if (goal.duration_unit === 'months') {
            setBreakdownGoalId(goal.id); // Ask user preference
        } else {
            handleDecompose(goal.id, 'daily');
        }
    }

    const handleDecompose = async (id: number, breakdownType: 'daily' | 'weekly') => {
        setBreakdownGoalId(null);
        setProcessingId(id);
        try {
            const updatedGoal = await decomposeGoal(id, breakdownType);
            setGoals(prev => prev.map(g => g.id === id ? updatedGoal : g));
            setExpandingId(id); // Auto expand to show steps
        } catch (e) {
            console.error("Failed to decompose", e);
        } finally {
            setProcessingId(null);
        }
    };

    const toggleSubtask = async (goal: Goal, index: number) => {
        const subtasks = getSubtasks(goal.subtasks);
        if (subtasks[index] && typeof subtasks[index] === 'object') {
            subtasks[index].completed = !subtasks[index].completed;
        } else {
            return;
        }

        const allCompleted = subtasks.length > 0 && subtasks.every((t: any) => t.completed);
        let newStatus = goal.status;

        if (allCompleted && goal.status !== 'completed') {
            newStatus = 'completed';
        } else if (!allCompleted && goal.status === 'completed') {
            newStatus = 'in_progress';
        }

        // Optimistic Update
        const updatedSubtasksJson = JSON.stringify(subtasks);
        setGoals(prev => prev.map(g => g.id === goal.id ? { ...g, subtasks: updatedSubtasksJson, status: newStatus } : g));

        try {
            await updateGoal(goal.id, { subtasks: updatedSubtasksJson, status: newStatus });
        } catch (e) {
            console.error("Failed to update subtask", e);
            loadGoals(); // Revert
        }
    }

    // ... (rest of the file until rendering subtasks)

    const toggleStatus = async (goal: Goal) => {
        const newStatus = goal.status === 'completed' ? 'in_progress' : 'completed';
        try {
            setGoals(prev => prev.map(g => g.id === goal.id ? { ...g, status: newStatus } : g));
            await updateGoal(goal.id, { status: newStatus });
        } catch (e) {
            console.error("Failed to update status", e);
            loadGoals(); // Revert
        }
    };

    const openNewGoalModal = () => {
        setEditingGoal({
            title: "",
            description: "",
            duration: 7,
            duration_unit: "days",
            priority: "Medium"
        });
        setIsEditModalOpen(true);
    };

    const openEditModal = (goal: Goal) => {
        setEditingGoal({ ...goal });
        setIsEditModalOpen(true);
    }

    const getSubtasks = (jsonStr: string) => {
        try {
            const parsed = JSON.parse(jsonStr);
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    };

    const handleTakeQuiz = async (goalId: number) => {
        setLoadingQuiz(true);
        try {
            const data = await getGoalQuiz(goalId);
            if (data.available && data.quiz) {
                setQuizData(data.quiz);
                setCurrentQuestionIndex(0);
                setScore(0);
                setShowResults(false);
                setIsQuizOpen(true);
            } else {
                alert("No quiz available for this goal yet. Complete all tasks first!");
            }
        } catch (e) {
            console.error("Failed to fetch quiz", e);
        } finally {
            setLoadingQuiz(false);
        }
    };

    const handleAnswer = (selectedOption: string) => {
        const currentQuestion = quizData.questions[currentQuestionIndex];
        // Simple check: assuming backend provides "correct_answer" that matches option text or index
        // The backend prompt asked for "correct_answer" text.

        // Let's assume exact text match for now
        if (selectedOption === currentQuestion.correct_answer) {
            setScore(prev => prev + 1);
        }

        if (currentQuestionIndex + 1 < quizData.questions.length) {
            setCurrentQuestionIndex(prev => prev + 1);
        } else {
            setShowResults(true);
        }
    };

    return (
        <div className="p-4">
            {/* Breakdown Choice Modal */}
            <AnimatePresence>
                {breakdownGoalId && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="bg-zinc-900 border border-white/10 w-full max-w-sm rounded-2xl p-6 shadow-2xl"
                        >
                            <h3 className="text-lg font-bold text-white mb-2">Choose Breakdown Style</h3>
                            <p className="text-muted text-sm mb-6">How would you like to plan this goal?</p>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => handleDecompose(breakdownGoalId, 'daily')}
                                    className="p-4 rounded-xl bg-white/5 hover:bg-primary/20 hover:border-primary/50 border border-white/10 flex flex-col items-center gap-2 transition-all"
                                >
                                    <span className="font-bold text-white">Daily Plan</span>
                                    <span className="text-xs text-muted">Detailed day-by-day steps</span>
                                </button>
                                <button
                                    onClick={() => handleDecompose(breakdownGoalId, 'weekly')}
                                    className="p-4 rounded-xl bg-white/5 hover:bg-secondary/20 hover:border-secondary/50 border border-white/10 flex flex-col items-center gap-2 transition-all"
                                >
                                    <span className="font-bold text-white">Weekly Plan</span>
                                    <span className="text-xs text-muted">Broader weekly milestones</span>
                                </button>
                            </div>
                            <button onClick={() => setBreakdownGoalId(null)} className="w-full mt-4 text-xs text-muted hover:text-white">Cancel</button>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>


            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <p className="text-muted text-sm font-medium">Manage, Track, and Crush your goals.</p>
                <button
                    onClick={openNewGoalModal}
                    className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-xl font-medium shadow-lg shadow-primary/20 transition-all active:scale-95"
                >
                    <Plus className="w-5 h-5" />
                    New Goal
                </button>
            </div>

            {loading ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="w-8 h-8 animate-spin text-primary" />
                </div>
            ) : goals.length === 0 ? (
                <div className="text-center py-16 border-2 border-dashed border-border/40 rounded-2xl bg-surface/30">
                    <Target className="w-16 h-16 mx-auto mb-4 text-muted/50" />
                    <h3 className="text-xl font-medium text-text">No active goals</h3>
                    <p className="text-muted mt-2 mb-6">Start by creating a new goal manually or ask Lumina to help.</p>
                </div>
            ) : (
                <div className="grid gap-5 md:grid-cols-1 lg:grid-cols-2">
                    <AnimatePresence>
                        {goals.map(goal => (
                            <motion.div
                                key={goal.id}
                                layout
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.95 }}
                                className={`group relative bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl overflow-hidden hover:shadow-xl transition-all duration-300 ${goal.status === 'completed' ? 'opacity-70' : ''}`}
                            >
                                {/* Decorative Gradient Blob */}
                                <div className="absolute top-0 right-0 -mt-16 -mr-16 w-32 h-32 bg-primary/20 rounded-full blur-3xl pointer-events-none group-hover:bg-primary/30 transition-all"></div>

                                <div className="p-6 relative z-10">
                                    {/* Top Row: Check + Title + Actions */}
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-start gap-4 flex-1">
                                            <button
                                                onClick={() => toggleStatus(goal)}
                                                className={`mt-1 flex-shrink-0 transition-all duration-300 ${goal.status === 'completed'
                                                    ? 'text-green-500 scale-110'
                                                    : 'text-muted hover:text-primary'
                                                    }`}
                                            >
                                                {goal.status === 'completed' ?
                                                    <CheckCircle2 className="w-6 h-6 fill-green-500/20" /> :
                                                    <Circle className="w-6 h-6" />
                                                }
                                            </button>

                                            <div className="flex-1 min-w-0">
                                                <h3 className={`text-lg font-bold truncate transition-all ${goal.status === 'completed' ? 'text-muted line-through decoration-2' : 'text-text'}`}>
                                                    {goal.title}
                                                </h3>
                                                {goal.description && <p className="text-sm text-muted truncate mt-1">{goal.description}</p>}

                                                <div className="flex flex-wrap items-center gap-2 mt-3 text-xs font-medium">
                                                    {/* Priority Badge */}
                                                    <span className={`px-2 py-1 rounded-md border ${goal.priority === 'High' ? 'bg-red-500/10 border-red-500/20 text-red-500' :
                                                        goal.priority === 'Medium' ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' :
                                                            'bg-blue-500/10 border-blue-500/20 text-blue-500'
                                                        }`}>
                                                        {goal.priority}
                                                    </span>

                                                    {/* Duration Badge */}
                                                    <span className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface border border-white/5 text-muted">
                                                        <Clock className="w-3.5 h-3.5" />
                                                        {goal.duration} {goal.duration === 1 && goal.duration_unit.endsWith('s') ? goal.duration_unit.slice(0, -1) : goal.duration_unit}
                                                    </span>

                                                    {/* Due Date Badge */}
                                                    {goal.created_at && (() => {
                                                        const dueDate = new Date(goal.created_at);
                                                        if (goal.duration === undefined || goal.duration === null) return null;

                                                        // Calculate Due Date
                                                        if (goal.duration_unit === 'weeks') dueDate.setDate(dueDate.getDate() + goal.duration * 7);
                                                        else if (goal.duration_unit === 'months') dueDate.setMonth(dueDate.getMonth() + goal.duration);
                                                        else dueDate.setDate(dueDate.getDate() + goal.duration);

                                                        // Check Overdue (compare with today)
                                                        const today = new Date();
                                                        // Reset time part for accurate day comparison
                                                        today.setHours(0, 0, 0, 0);
                                                        const checkDate = new Date(dueDate);
                                                        checkDate.setHours(0, 0, 0, 0);

                                                        const isOverdue = checkDate < today;
                                                        const isCompleted = goal.status === 'completed';
                                                        const isOverdueAndActive = isOverdue && !isCompleted;

                                                        return (
                                                            <span className={`flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface border border-white/5 transition-colors ${isOverdueAndActive ? 'text-red-400 border-red-500/20 bg-red-500/5' : 'text-muted'}`}>
                                                                <CalendarCheck className={`w-3.5 h-3.5 ${isOverdueAndActive ? 'text-red-500' : 'text-blue-400'}`} />
                                                                {isOverdueAndActive ? "Overdue: " : "Due: "}
                                                                {dueDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric' })}
                                                            </span>
                                                        );
                                                    })()}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Action Buttons */}
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={() => openEditModal(goal)}
                                                className="p-2 text-muted hover:text-primary hover:bg-primary/10 rounded-lg transition-colors"
                                                title="Edit Goal"
                                            >
                                                <Edit2 className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => setDeleteId(goal.id)}
                                                className="p-2 text-muted hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors"
                                                title="Delete Goal"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Roadmap Section */}
                                    <div className="mt-5 pt-4 border-t border-white/5">
                                        {getSubtasks(goal.subtasks).length > 0 ? (
                                            <div>
                                                <button
                                                    onClick={() => setExpandingId(expandingId === goal.id ? null : goal.id)}
                                                    className="w-full flex items-center justify-between group/btn text-sm font-medium text-text/80 hover:text-text bg-surface/50 hover:bg-surface border border-white/5 rounded-lg px-3 py-2 transition-all"
                                                >
                                                    <div className="flex items-center gap-2">
                                                        <Target className="w-4 h-4 text-secondary" />
                                                        <span>View Roadmap</span>
                                                        <span className="bg-primary/20 text-primary text-[10px] px-1.5 py-0.5 rounded-full">
                                                            {getSubtasks(goal.subtasks).filter((t: any) => typeof t === 'object' ? t.completed : false).length} / {getSubtasks(goal.subtasks).length}
                                                        </span>
                                                    </div>
                                                    {expandingId === goal.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                                </button>

                                                <AnimatePresence>
                                                    {expandingId === goal.id && (
                                                        <motion.div
                                                            initial={{ height: 0, opacity: 0 }}
                                                            animate={{ height: 'auto', opacity: 1 }}
                                                            exit={{ height: 0, opacity: 0 }}
                                                            className="overflow-hidden"
                                                        >
                                                            <div className="mt-3 space-y-2 pl-1">
                                                                {getSubtasks(goal.subtasks).map((step: any, i: number) => {
                                                                    const isObj = typeof step === 'object';
                                                                    const text = isObj ? step.text : step;
                                                                    const isCompleted = isObj ? step.completed : false;

                                                                    return (
                                                                        <div
                                                                            key={i}
                                                                            onClick={() => toggleSubtask(goal, i)}
                                                                            className={`flex gap-3 text-sm cursor-pointer group/step p-2 rounded-lg transition-all ${isCompleted ? 'text-muted decoration-line-through' : 'text-text hover:bg-white/5'}`}
                                                                        >
                                                                            <div className={`mt-0.5 w-5 h-5 rounded-full border flex items-center justify-center transition-all ${isCompleted ? 'bg-secondary border-secondary' : 'border-muted hover:border-secondary'}`}>
                                                                                {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                                                                            </div>
                                                                            <span className={`flex-1 ${isCompleted ? 'text-muted' : ''}`}>{text}</span>
                                                                        </div>
                                                                    );
                                                                })}

                                                                <button
                                                                    onClick={() => handleDecomposeClick(goal)}
                                                                    className="text-xs text-secondary hover:underline ml-2 mt-4 flex items-center gap-1 opacity-80 hover:opacity-100"
                                                                >
                                                                    <RefreshCw className="w-3 h-3" />
                                                                    Regenerate Goal Plan
                                                                </button>
                                                            </div>

                                                            {/* Quiz Button if Completed */}
                                                            {getSubtasks(goal.subtasks).every((t: any) => typeof t === 'object' && t.completed) && (
                                                                <div className="mt-4 px-2">
                                                                    <button
                                                                        onClick={() => handleTakeQuiz(goal.id)}
                                                                        disabled={loadingQuiz}
                                                                        className="w-full py-3 bg-gradient-to-r from-purple-500/10 to-blue-500/10 hover:from-purple-500/20 hover:to-blue-500/20 border border-purple-500/20 rounded-xl flex items-center justify-center gap-2 group/quiz transition-all"
                                                                    >
                                                                        {loadingQuiz ? <Loader2 className="w-5 h-5 animate-spin text-purple-400" /> : <BrainCircuit className="w-5 h-5 text-purple-400 group-hover/quiz:rotate-12 transition-transform" />}
                                                                        <span className="font-bold text-purple-200 group-hover/quiz:text-white">Take Knowledge Quiz</span>
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={() => handleDecomposeClick(goal)}
                                                disabled={processingId === goal.id}
                                                className="w-full relative overflow-hidden group/gen py-2.5 rounded-xl bg-gradient-to-r from-secondary/10 to-primary/10 hover:from-secondary/20 hover:to-primary/20 border border-white/5 text-sm font-medium text-text flex items-center justify-center gap-2 transition-all"
                                            >
                                                {processingId === goal.id ? (
                                                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                                ) : (
                                                    <CalendarCheck className="w-4 h-4 text-secondary group-hover/gen:scale-110 transition-transform" />
                                                )}
                                                {processingId === goal.id ? "Creating Plan..." : "Smart Goal Planner"}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}

            {/* --- Modals --- */}

            {/* Create/Edit Modal */}
            <AnimatePresence>
                {isEditModalOpen && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: 20 }}
                            className="bg-white dark:bg-zinc-900 border border-gray-200 dark:border-white/10 w-full max-w-md max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <form onSubmit={handleSaveGoal}>
                                <div className="px-6 py-4 border-b border-gray-100 dark:border-white/5 flex justify-between items-center bg-white/60 dark:bg-zinc-900/60 sticky top-0 backdrop-blur-xl z-20">
                                    <h3 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                        {editingGoal?.id ? <Edit2 className="w-5 h-5 text-secondary" /> : <Plus className="w-5 h-5 text-primary" />}
                                        {editingGoal?.id ? "Edit Goal" : "New Goal"}
                                    </h3>
                                    <button
                                        type="button"
                                        onClick={() => setIsEditModalOpen(false)}
                                        className="text-muted hover:text-gray-900 dark:hover:text-white bg-transparent p-1 rounded-md hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                <div className="p-6 space-y-6">
                                    {/* Title Input */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-2">
                                            <Target className="w-4 h-4 text-primary" /> Title
                                        </label>
                                        <input
                                            autoFocus
                                            type="text"
                                            value={editingGoal?.title || ""}
                                            onChange={e => setEditingGoal(prev => ({ ...prev, title: e.target.value }))}
                                            placeholder="What do you want to achieve?"
                                            className="w-full bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-lg text-gray-900 dark:text-white placeholder:text-muted/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-medium"
                                            required
                                        />
                                    </div>

                                    {/* Description Input */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-2">
                                            Description <span className="text-muted/50 font-normal normal-case">(Optional)</span>
                                        </label>
                                        <textarea
                                            value={editingGoal?.description || ""}
                                            onChange={e => setEditingGoal(prev => ({ ...prev, description: e.target.value }))}
                                            placeholder="Add details, success criteria, or notes..."
                                            className="w-full bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-gray-900 dark:text-white placeholder:text-muted/50 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all resize-none h-24 leading-relaxed"
                                        />
                                    </div>

                                    {/* Duration */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-2">
                                            <Clock className="w-4 h-4 text-primary" /> Duration
                                        </label>
                                        <div className="grid grid-cols-5 gap-3">
                                            <div className="col-span-2">
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={editingGoal?.duration || 1}
                                                    onChange={e => setEditingGoal(prev => ({ ...prev, duration: parseInt(e.target.value) || 1 }))}
                                                    className="w-full bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-center text-gray-900 dark:text-white focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono"
                                                />
                                            </div>
                                            <div className="col-span-3 relative">
                                                <select
                                                    value={editingGoal?.duration_unit || "days"}
                                                    onChange={e => setEditingGoal(prev => ({ ...prev, duration_unit: e.target.value }))}
                                                    className="w-full bg-gray-100 dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-xl px-4 py-3 text-gray-900 dark:text-white focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 appearance-none cursor-pointer transition-all"
                                                >
                                                    <option value="days" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">Days</option>
                                                    <option value="weeks" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">Weeks</option>
                                                    <option value="months" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white">Months</option>
                                                </select>
                                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted pointer-events-none" />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Priority Selection */}
                                    <div className="space-y-3">
                                        <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-2">
                                            Priority Level
                                        </label>
                                        <div className="flex gap-3">
                                            {['Low', 'Medium', 'High'].map(p => (
                                                <button
                                                    key={p}
                                                    type="button"
                                                    onClick={() => setEditingGoal(prev => ({ ...prev, priority: p }))}
                                                    className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all border flex items-center justify-center gap-2 ${editingGoal?.priority === p
                                                        ? p === 'High' ? 'bg-red-500/10 border-red-500 text-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)] scale-[1.02]' :
                                                            p === 'Medium' ? 'bg-amber-500/10 border-amber-500 text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)] scale-[1.02]' :
                                                                'bg-blue-500/10 border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.2)] scale-[1.02]'
                                                        : 'bg-gray-100 dark:bg-gray-900 text-muted border-gray-200 dark:border-white/5 hover:bg-gray-200 dark:hover:bg-white/10 hover:text-gray-900 dark:hover:text-white'
                                                        }`}
                                                >
                                                    {p === 'High' && <AlertTriangle className="w-4 h-4" />}
                                                    {p}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="p-6 border-t border-gray-100 dark:border-white/5 flex justify-end gap-3 bg-gray-50/50 dark:bg-white/5">
                                    <button
                                        type="button"
                                        onClick={() => setIsEditModalOpen(false)}
                                        className="px-6 py-2.5 text-sm font-medium text-muted hover:text-white transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="px-6 py-2.5 bg-primary hover:bg-primary/90 text-white rounded-xl font-bold shadow-lg shadow-primary/20 flex items-center gap-2 transition-transform active:scale-95"
                                    >
                                        Save Goal
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Delete Confirmation Modal */}
            <AnimatePresence>
                {deleteId && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20 }}
                            className="bg-zinc-900 border border-white/10 w-full max-w-sm rounded-2xl shadow-2xl p-6"
                        >
                            <div className="flex flex-col items-center text-center">
                                <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
                                    <AlertTriangle className="w-6 h-6 text-red-500" />
                                </div>
                                <h3 className="text-xl font-bold text-white mb-2">Delete Goal?</h3>
                                <p className="text-muted text-sm mb-6">
                                    Are you sure you want to delete this goal? This action cannot be undone.
                                </p>
                                <div className="flex gap-3 w-full">
                                    <button
                                        onClick={() => setDeleteId(null)}
                                        className="flex-1 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white font-medium transition-colors"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={confirmDelete}
                                        className="flex-1 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white font-medium shadow-lg shadow-red-500/20 transition-colors"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>

            {/* Quiz Modal */}
            <AnimatePresence>
                {isQuizOpen && quizData && (
                    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="bg-zinc-900 border border-purple-500/20 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden"
                        >
                            {!showResults && quizData.questions && quizData.questions.length > 0 ? (
                                <div className="p-8">
                                    <div className="flex justify-between items-center mb-6">
                                        <div className="flex items-center gap-2 text-purple-400">
                                            <BrainCircuit className="w-6 h-6" />
                                            <span className="font-bold tracking-wider uppercase text-sm">Knowledge Check</span>
                                        </div>
                                        <span className="text-muted font-mono text-sm">Question {currentQuestionIndex + 1}/{quizData.questions.length}</span>
                                    </div>

                                    <h3 className="text-xl md:text-2xl font-bold text-white mb-8">
                                        {quizData.questions[currentQuestionIndex].question}
                                    </h3>

                                    <div className="grid gap-3">
                                        {quizData.questions[currentQuestionIndex].options.map((option: string, idx: number) => (
                                            <button
                                                key={idx}
                                                onClick={() => handleAnswer(option)}
                                                className="w-full text-left p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-purple-500/50 transition-all font-medium text-gray-200 hover:text-white hover:pl-5 duration-200"
                                            >
                                                <span className="inline-block w-6 text-muted">{String.fromCharCode(65 + idx)}.</span> {option}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ) : showResults ? (
                                <div className="p-12 text-center flex flex-col items-center">
                                    <div className="w-20 h-20 bg-purple-500/20 rounded-full flex items-center justify-center mb-6">
                                        <Target className="w-10 h-10 text-purple-500" />
                                    </div>
                                    <h3 className="text-3xl font-bold text-white mb-2">Quiz Completed!</h3>
                                    <p className="text-muted mb-8">You've tested your knowledge on this goal.</p>

                                    <div className="text-6xl font-black text-transparent bg-clip-text bg-gradient-to-tr from-purple-400 to-blue-400 mb-2">
                                        {score}/{quizData.questions.length}
                                    </div>
                                    <p className="text-sm font-bold uppercase tracking-widest text-muted mb-8">Final Score</p>

                                    <button
                                        onClick={() => setIsQuizOpen(false)}
                                        className="bg-white text-black px-8 py-3 rounded-xl font-bold hover:bg-gray-200 transition-colors"
                                    >
                                        Close Quiz
                                    </button>
                                </div>
                            ) : (
                                <div className="p-8 text-center text-red-400">
                                    <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                                    <h3 className="text-lg font-bold">Quiz Data Error</h3>
                                    <p className="text-sm mt-2">Could not load questions.</p>
                                    <button onClick={() => setIsQuizOpen(false)} className="mt-4 text-white hover:underline">Close</button>
                                </div>
                            )}
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
