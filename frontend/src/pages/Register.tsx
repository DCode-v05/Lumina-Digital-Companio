import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../api';
import { Brain, Loader2 } from 'lucide-react';

export default function Register() {
    const [email, setEmail] = useState('');
    const [fullname, setFullname] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            await register(email, password, fullname);
            // Auto redirect to login
            navigate('/login');
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Registration failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-background px-4">
            <div className="w-full max-w-md space-y-8 rounded-2xl border border-border bg-surface p-8 shadow-2xl transition-colors">
                <div className="text-center">
                    <div className="mx-auto w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center text-secondary mb-4">
                        <Brain className="w-6 h-6" />
                    </div>
                    <h2 className="text-3xl font-bold tracking-tight text-text mb-2">Create Account</h2>
                    <p className="text-sm text-muted">Join Lumina and start learning smarter</p>
                </div>

                <form className="space-y-6" onSubmit={handleRegister}>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text">Full Name</label>
                        <input
                            type="text"
                            required
                            value={fullname}
                            onChange={(e) => setFullname(e.target.value)}
                            className="w-full rounded-lg border border-border bg-input p-3 text-text placeholder-muted focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary transition-colors"
                            placeholder="John Doe"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text">Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full rounded-lg border border-border bg-input p-3 text-text placeholder-muted focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary transition-colors"
                            placeholder="you@example.com"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-text">Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full rounded-lg border border-border bg-input p-3 text-text placeholder-muted focus:border-secondary focus:outline-none focus:ring-1 focus:ring-secondary transition-colors"
                            placeholder="••••••••"
                        />
                    </div>

                    {error && <p className="text-sm text-red-500 text-center">{error}</p>}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full rounded-lg bg-secondary py-3 font-semibold text-white hover:bg-emerald-600 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-2 transition-colors"
                    >
                        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                        Create Account
                    </button>
                </form>

                <p className="text-center text-sm text-muted">
                    Already have an account?{' '}
                    <Link to="/login" className="font-semibold text-secondary hover:text-emerald-400 transition-colors">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    );
}
