"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { supabase } from "@/lib/supabase";

export default function AuroraDashboard() {
    const { user, session, loading, signOut } = useAuth();
    const [activeTab, setActiveTab] = useState("pipeline");
    const [status, setStatus] = useState<any>({ running: false, progress: 0, logs: [], video_url: null });
    const [topic, setTopic] = useState("");
    const [autoTrending, setAutoTrending] = useState(false);
    const [runMode, setRunMode] = useState("full");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [authLoading, setAuthLoading] = useState(false);
    const [authMode, setAuthMode] = useState<"login" | "signup">("login");
    const [profileName, setProfileName] = useState("");
    const [launchingProfile, setLaunchingProfile] = useState(false);

    // Settings State
    const [settings, setSettings] = useState<any>({
        api_keys: { gemini: "", elevenlabs: "", google_tts: "", fal_ai: "", replicate: "", stable_horde: "" },
        tts: { backend: "edge_tts", chatterbox_path: "", chatterbox_reference_audio: "my_voice_reference.wav", edge_tts_voice: "hi-IN-MadhurNeural", elevenlabs_voice_id: "" },
        image: { backend: "pollinations", comfyui_url: "http://127.0.0.1:8188", image_count: 6 },
        pipeline: { language: "hi", upload_mode: "unlisted", output_folder: "output", active_profile_index: 0, chrome_profiles: [] }
    });

    const [visibleKeys, setVisibleKeys] = useState<any>({});
    const toggleKeyVisibility = (key: string) => {
        setVisibleKeys({ ...visibleKeys, [key]: !visibleKeys[key] });
    };

    const apiFetch = async (endpoint: string, options: any = {}) => {
        const url = `http://localhost:8000${endpoint}`;
        const headers = {
            ...options.headers,
            "Authorization": `Bearer ${session?.access_token}`,
        };
        return fetch(url, { ...options, headers });
    };

    // Polling
    useEffect(() => {
        if (!user) return;
        let intervalId: any;
        const fetchStatus = async () => {
            try {
                const res = await apiFetch("/api/pipeline/status");
                if (res.ok) setStatus(await res.json());
            } catch (err) { }
        };

        if (activeTab === "pipeline") {
            fetchStatus(); // Fetch once right when tab is opened
        }

        // Only run interval if pipeline is actually running to avoid network spam
        if (status.running) {
            intervalId = setInterval(fetchStatus, 3000);
        }
        return () => clearInterval(intervalId);
    }, [status.running, activeTab, user, session]);

    // Initial Sync
    useEffect(() => {
        if (!user) return;
        const fetchAll = async () => {
            try {
                const res = await apiFetch("/api/settings");
                if (res.ok) setSettings(await res.json());
            } catch (err) { }
        };
        fetchAll();
    }, [user, session]);

    const runPipeline = async () => {
        setStatus((prev: any) => ({ ...prev, running: true, progress: 0, logs: ["[INFO] Starting sequence..."] }));
        await apiFetch("/api/pipeline/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ topic: autoTrending ? null : topic, language: settings.pipeline.language, mode: runMode }),
        });
    };

    const abortPipeline = async () => {
        await apiFetch("/api/pipeline/abort", {
            method: "POST"
        });
    };

    const saveSettings = async () => {
        await apiFetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings),
        });
        alert("Configuration Persistent in Sync Core");
    };

    const setupNewProfile = async () => {
        if (!profileName.trim()) {
            alert("Please enter a name for the profile");
            return;
        }
        setLaunchingProfile(true);
        try {
            const res = await apiFetch("/api/settings/setup_profile", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name: profileName }),
            });
            if (res.ok) {
                alert("Setup window launched! Check your desktop to log in to YouTube.");
                setProfileName("");
            } else {
                alert("Failed to launch setup window.");
            }
        } catch (err) {
            alert("Error launching setup.");
        }
        setLaunchingProfile(false);
    };

    const removeProfile = async (index: number) => {
        if (!confirm("Are you sure you want to remove this profile?")) return;
        try {
            const res = await apiFetch(`/api/settings/profile/${index}`, {
                method: "DELETE",
            });
            if (res.ok) {
                // Refresh local state
                const sres = await apiFetch("/api/settings");
                if (sres.ok) setSettings(await sres.json());
            }
        } catch (err) {
            alert("Error removing profile.");
        }
    };

    const scanExistingProfiles = async () => {
        try {
            const res = await apiFetch("/api/settings/profiles/scan");
            if (res.ok) {
                const found = await res.json();
                if (found.length === 0) {
                    alert("No existing 'GhostCreator' profiles found in D:\\ChromeProfiles.");
                    return;
                }
                
                // Merge with existing but avoid duplicates by path
                const currentPaths = new Set(settings.pipeline.chrome_profiles.map((p: any) => p.path));
                const toAdd = found.filter((p: any) => !currentPaths.has(p.path));
                
                if (toAdd.length === 0) {
                    alert("All found profiles are already in your list.");
                    return;
                }

                if (confirm(`Found ${toAdd.length} existing profiles. Import them?`)) {
                    const newSettings = {
                        ...settings,
                        pipeline: {
                            ...settings.pipeline,
                            chrome_profiles: [...settings.pipeline.chrome_profiles, ...toAdd]
                        }
                    };
                    setSettings(newSettings);
                    // Autosave
                    await apiFetch("/api/settings", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(newSettings),
                    });
                    alert("Profiles imported and synced!");
                }
            }
        } catch (err) {
            alert("Error scanning profiles.");
        }
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthLoading(true);
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) alert(error.message);
        setAuthLoading(false);
    };

    const handleSignUp = async (e: React.FormEvent) => {
        e.preventDefault();
        setAuthLoading(true);
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) alert(error.message);
        else alert("Check your email for confirmation!");
        setAuthLoading(false);
    };

    if (loading) {
        return <div className="main_wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: 'var(--accent-pri)' }}>
            <div className="Orbitron" style={{ fontSize: '14px' }}>INITIALIZING NEURAL LINK...</div>
        </div>;
    }

    if (!user) {
        const isSignup = authMode === "signup";
        return (
            <div className="main_wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
                <div className="glass" style={{ width: '420px', padding: '40px', borderRadius: '16px', border: '1px solid var(--border)', textAlign: 'center' }}>
                    <div style={{ fontSize: '44px', marginBottom: '16px' }}>👻</div>
                    <h1 className="Orbitron" style={{ fontSize: '18px', marginBottom: '6px' }}>GHOST <span style={{ color: 'var(--accent-pri)' }}>CREATOR AI</span></h1>
                    <p className="Mono" style={{ fontSize: '10px', color: 'var(--text-sec)', marginBottom: '28px' }}>AUTHORIZATION LAYER v2.5</p>

                    {/* Mode Toggle */}
                    <div style={{ display: 'flex', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', padding: '4px', marginBottom: '28px', border: '1px solid var(--border)' }}>
                        <button
                            onClick={() => setAuthMode("login")}
                            style={{ flex: 1, padding: '10px', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', borderRadius: '6px', border: 'none', cursor: 'pointer', transition: 'all 0.2s', background: !isSignup ? 'var(--accent-pri)' : 'transparent', color: !isSignup ? '#000' : 'var(--text-sec)' }}
                        >LOGIN</button>
                        <button
                            onClick={() => setAuthMode("signup")}
                            style={{ flex: 1, padding: '10px', fontSize: '11px', fontWeight: 700, letterSpacing: '1px', borderRadius: '6px', border: 'none', cursor: 'pointer', transition: 'all 0.2s', background: isSignup ? 'var(--accent-pri)' : 'transparent', color: isSignup ? '#000' : 'var(--text-sec)' }}
                        >SIGN UP</button>
                    </div>

                    <form onSubmit={isSignup ? handleSignUp : handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <input type="email" placeholder="Email Address" value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" style={{ width: '100%' }} required />
                        <input type="password" placeholder={isSignup ? "Choose a Password (min 6 chars)" : "Password"} value={password} onChange={(e) => setPassword(e.target.value)} className="input-field" style={{ width: '100%' }} required />
                        <button type="submit" disabled={authLoading} className="btn-primary" style={{ width: '100%', padding: '13px', fontSize: '12px', fontWeight: 800, letterSpacing: '2px', marginTop: '6px' }}>
                            {authLoading ? "SYNCHRONIZING..." : isSignup ? "CREATE GHOST ID" : "LOGIN TO HUB"}
                        </button>
                    </form>

                    <p className="Mono" style={{ marginTop: '24px', fontSize: '10px', color: 'var(--text-sec)' }}>
                        {isSignup ? "Already have an account? " : "No account yet? "}
                        <span onClick={() => setAuthMode(isSignup ? "login" : "signup")} style={{ color: 'var(--accent-pri)', cursor: 'pointer', textDecoration: 'underline' }}>
                            {isSignup ? "Login here" : "Create one now"}
                        </span>
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="main_wrapper" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'transparent', overflow: 'hidden' }}>

            {/* HEADER */}
            <header className="glass" style={{ padding: '12px 40px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', zIndex: 100, borderTop: 'none', borderLeft: 'none', borderRight: 'none' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                    <div className="pulse" style={{ width: '28px', height: '28px', border: '1.5px solid var(--accent-pri)', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginRight: '12px', background: 'var(--accent-pri-glow)' }}>
                        <span style={{ fontSize: '14px' }}>👻</span>
                    </div>
                    <div>
                        <h1 className="Orbitron" style={{ fontSize: '13px', letterSpacing: '2px', fontWeight: 800, margin: 0 }}>GHOST CREATOR <span style={{ color: 'var(--accent-pri)' }}>AI</span></h1>
                        <p className="Mono" style={{ fontSize: '9px', color: 'var(--accent-pri)', opacity: 0.8, letterSpacing: '1px' }}>SYNAPTIC CORE v2.5_PRO | {user.email}</p>
                    </div>
                </div>

                <nav style={{ display: 'flex', gap: '6px', background: 'rgba(0,0,0,0.4)', padding: '5px', borderRadius: '10px', border: '1px solid var(--border)' }}>
                    <button onClick={() => setActiveTab("pipeline")} className={`tab-btn ${activeTab === 'pipeline' ? 'active' : ''}`}>▶ PIPELINE</button>
                    <button onClick={() => setActiveTab("settings")} className={`tab-btn ${activeTab === 'settings' ? 'active' : ''}`}>⚙ SETTINGS</button>
                    <button onClick={() => setActiveTab("history")} className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}>📜 HISTORY</button>
                </nav>

                <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                    <div className="glass" style={{ borderRadius: '6px', padding: '6px 15px', color: 'var(--accent-pri)', fontSize: '10px', fontWeight: 800, border: '1px solid var(--accent-pri-glow)' }}>
                        <span className="pulse" style={{ marginRight: '8px' }}>●</span> SYSTEM READY
                    </div>
                    <button onClick={signOut} className="btn-outline-red" style={{ padding: '6px 12px', fontSize: '9px' }}>LOGOUT</button>
                </div>
            </header>

            <main style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>

                {activeTab === "pipeline" && (
                    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                        <div style={{ border: '1px solid #111', borderRadius: '8px', padding: '40px', background: 'rgba(5,5,10,0.5)' }}>

                            <div className="chip-group" style={{ marginBottom: '25px' }}>
                                {['FULL', 'SKIP IMAGES', 'FROM VIDEO'].map(m => (
                                    <div key={m} onClick={() => setRunMode(m.toLowerCase().replace(' ', '_'))} className={`chip ${runMode === m.toLowerCase().replace(' ', '_') ? 'active-cyan' : ''}`} style={{ flex: 'none', width: '150px' }}>{m}</div>
                                ))}
                            </div>

                            <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
                                <div style={{ flex: 1, position: 'relative' }}>
                                    <span style={{ position: 'absolute', left: '15px', top: '50%', transform: 'translateY(-50%)', fontSize: '10px', color: 'var(--accent-sec)', fontFamily: 'Orbitron' }}>NEURAL PROMPT ›</span>
                                    <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Enter topic or leave blank for auto-trending..." style={{ width: '100%', padding: '14px 14px 14px 130px', background: 'rgba(255,255,255,0.02)', border: '1px solid #222', borderRadius: '4px', color: '#fff', fontSize: '12px' }} />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }} onClick={() => setAutoTrending(!autoTrending)}>
                                    <input type="checkbox" checked={autoTrending} readOnly style={{ width: '18px', height: '18px', accentColor: 'var(--accent-pri)' }} />
                                    <span style={{ fontSize: '10px', color: 'var(--text-sec)', fontFamily: 'Orbitron' }}>AUTO-TRENDING</span>
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '15px', marginBottom: '40px' }}>
                                <button onClick={runPipeline} className="btn-primary" style={{ padding: '12px 40px', fontSize: '12px' }}>▶ INITIALIZE SEQUENCE</button>
                                <button onClick={abortPipeline} className="btn-outline-red" style={{ padding: '12px 40px', fontSize: '12px' }}>■ ABORT</button>
                            </div>

                            <div style={{ position: 'relative', margin: '60px 0', padding: '0 40px' }}>
                                <div className="progress-line"></div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                    {[{ id: 1, label: 'RESEARCH' }, { id: 2, label: 'SCRIPT' }, { id: 3, label: 'VOICE' }, { id: 4, label: 'IMAGES' }, { id: 5, label: 'VIDEO' }, { id: 6, label: 'UPLOAD' }]
                                        .map(stage => (
                                            <div key={stage.id} className="progress-node">
                                                <div className={`node-hex ${status.progress >= (stage.id * 16.6 - 8) ? 'active' : ''}`}>{stage.id}</div>
                                                <div className="node-label" style={{ color: status.progress >= (stage.id * 16.6 - 8) ? 'var(--accent-pri)' : 'var(--text-sec)' }}>{stage.label}</div>
                                            </div>
                                        ))}
                                </div>
                                <div style={{ marginTop: '30px', height: '6px', background: 'rgba(255,255,255,0.03)', borderRadius: '10px', overflow: 'hidden', position: 'relative' }}>
                                    <div style={{ width: `${status.progress}%`, height: '100%', background: 'linear-gradient(90deg, var(--accent-pri), var(--accent-sec))', boxShadow: '0 0 20px var(--accent-pri-glow)', transition: 'width 1s' }}></div>
                                </div>
                                <div style={{ textAlign: 'center', marginTop: '15px' }}>
                                    <span className="Mono" style={{ fontSize: '14px', color: 'var(--accent-pri)', fontWeight: 800, letterSpacing: '1px' }}>SYSTEM SYNC: {status.progress}%</span>
                                </div>
                            </div>

                            <div style={{ marginTop: '40px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                    <div style={{ fontSize: '10px', color: 'var(--accent-pri)', fontFamily: 'Orbitron' }}>⬡ TERMINAL OUTPUT |</div>
                                    {status.video_url && (
                                        <a href={`http://localhost:8000${status.video_url}`} target="_blank" className="btn-primary" style={{ padding: '5px 15px', fontSize: '9px', textDecoration: 'none' }}>
                                            📥 DOWNLOAD RECENT SHORT
                                        </a>
                                    )}
                                </div>
                                <div style={{ height: '300px', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border)', borderRadius: '8px', padding: '24px', overflowY: 'auto', fontFamily: 'Share Tech Mono', fontSize: '12px', color: '#94a3b8', boxShadow: 'inset 0 0 20px rgba(0,0,0,0.5)' }}>
                                    {status.logs.length === 0 ? (
                                        <div className="pulse" style={{ opacity: 0.3 }}>Waiting for neural uplink...</div>
                                    ) : (
                                        status.logs.map((log: string, i: number) => (
                                            <div key={i} style={{ marginBottom: '6px', borderLeft: '2px solid rgba(0,242,242,0.1)', paddingLeft: '15px' }}>
                                                <span style={{ color: 'var(--accent-pri)', opacity: 0.5, marginRight: '10px' }}>[{i.toString().padStart(3, '0')}]</span>
                                                {log}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === "settings" && (
                    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                        <div style={{ border: '1px solid #111', borderRadius: '8px', padding: '40px', background: 'rgba(5,5,10,0.5)', marginBottom: '100px' }}>

                            {/* API KEYS SECTION */}
                            <div className="settings-section-title">⬡ API KEYS</div>
                            {[
                                { id: 'gemini', label: 'GEMINI API KEY' },
                                { id: 'elevenlabs', label: 'ELEVENLABS API KEY' },
                                { id: 'google_tts', label: 'GOOGLE CLOUD TTS (JSON PATH)' },
                                { id: 'fal_ai', label: 'FAL.AI API KEY' },
                                { id: 'replicate', label: 'REPLICATE API KEY' },
                                { id: 'stable_horde', label: 'STABLE HORDE API KEY' }
                            ].map(key => (
                                <div key={key.id} className="settings-row">
                                    <label className="settings-label">{key.label}</label>
                                    <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', gap: '10px' }}>
                                        <input
                                            type={visibleKeys[key.id] ? "text" : "password"}
                                            className="input-field"
                                            style={{ flex: 1 }}
                                            value={settings.api_keys[key.id] || ""}
                                            onChange={(e) => setSettings({ ...settings, api_keys: { ...settings.api_keys, [key.id]: e.target.value } })}
                                        />
                                        <button onClick={() => toggleKeyVisibility(key.id)} style={{ background: 'transparent', border: '1px solid #222', color: 'var(--accent-pri)', padding: '8px', borderRadius: '4px', cursor: 'pointer' }}>
                                            {visibleKeys[key.id] ? "👓" : "👁️"}
                                        </button>
                                    </div>
                                </div>
                            ))}

                            {/* AUDIO SECTION */}
                            <div className="settings-section-title" style={{ marginTop: '40px' }}>⬡ AUDIO SUBROUTINE · <span style={{ color: 'var(--accent-sec)' }}>TTS BACKEND</span></div>
                            <div className="chip-group">
                                {['CHATTERBOX', 'EDGE TTS', 'ELEVENLABS', 'GOOGLE CLOUD', 'KOKORO TTS'].map(b => (
                                    <div key={b} onClick={() => setSettings({ ...settings, tts: { ...settings.tts, backend: b.toLowerCase().replace(' ', '_') } })} className={`chip ${settings.tts.backend === b.toLowerCase().replace(' ', '_') ? 'active' : ''}`}>{b}</div>
                                ))}
                            </div>
                            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #111', borderRadius: '4px', padding: '20px', marginBottom: '40px' }}>
                                <div className="settings-row">
                                    <label className="settings-label">EDGE TTS VOICE:</label>
                                    <select className="input-field" style={{ background: 'var(--accent-sec)', width: '250px' }} value={settings.tts.edge_tts_voice} onChange={(e) => setSettings({ ...settings, tts: { ...settings.tts, edge_tts_voice: e.target.value } })}>
                                        {["hi-IN-MadhurNeural", "hi-IN-SwaraNeural", "en-US-GuyNeural", "en-US-JennyNeural"].map(v => <option key={v}>{v}</option>)}
                                    </select>
                                </div>
                                <div className="settings-row">
                                    <label className="settings-label">ELEVENLABS VOICE ID:</label>
                                    <input className="input-field" style={{ width: '350px' }} value={settings.tts.elevenlabs_voice_id || ""} onChange={(e) => setSettings({ ...settings, tts: { ...settings.tts, elevenlabs_voice_id: e.target.value } })} />
                                </div>
                            </div>

                            {/* VISION SECTION (IMAGE BACKEND) */}
                            <div className="settings-section-title">⬡ VISION MATRIX · <span style={{ color: 'var(--accent-pri)' }}>IMAGE BACKEND</span></div>
                            <div className="chip-group">
                                {['COMFYUI', 'POLLINATIONS', 'IMAGEN-3'].map(b => (
                                    <div key={b} onClick={() => setSettings({ ...settings, image: { ...settings.image, backend: b.toLowerCase() } })} className={`chip ${settings.image.backend === b.toLowerCase() ? 'active-cyan' : ''}`}>{b}</div>
                                ))}
                            </div>
                            <div className="chip-group">
                                {['FAL.AI', 'STABLE HORDE', 'REPLICATE'].map(b => (
                                    <div key={b} onClick={() => setSettings({ ...settings, image: { ...settings.image, backend: b.toLowerCase().replace('.', '_') } })} className={`chip ${settings.image.backend === b.toLowerCase().replace('.', '_') ? 'active-cyan' : ''}`}>{b}</div>
                                ))}
                            </div>

                            {/* CORE PARAMETERS SECTION */}
                            <div className="settings-section-title">⬡ CORE PARAMETERS · <span style={{ color: '#ffd000' }}>PIPELINE</span></div>
                            <div className="settings-row">
                                <label className="settings-label">GEMINI MODEL ID:</label>
                                <select className="input-field" value={settings.pipeline.gemini_model} style={{ background: 'var(--accent-sec)', width: '250px' }} onChange={(e) => setSettings({ ...settings, pipeline: { ...settings.pipeline, gemini_model: e.target.value } })}>
                                    <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                                    <option value="gemini-2.0-flash">gemini-2.0-flash</option>
                                    <option value="gemini-2.5-flash">gemini-2.5-flash (v2.5 PRO)</option>
                                </select>
                            </div>
                            <div className="settings-row">
                                <label className="settings-label">LANGUAGE OVERRIDE:</label>
                                <select className="input-field" value={settings.pipeline.language} style={{ background: 'var(--accent-sec)', width: '150px' }} onChange={(e) => setSettings({ ...settings, pipeline: { ...settings.pipeline, language: e.target.value } })}>
                                    <option value="hi">hi</option>
                                    <option value="en">en</option>
                                    <option value="bn">bn</option>
                                </select>
                            </div>
                            <div className="settings-row">
                                <label className="settings-label">IMAGE COUNT:</label>
                                <select className="input-field" value={settings.image.image_count} style={{ background: 'var(--accent-sec)', width: '150px' }} onChange={(e) => setSettings({ ...settings, image: { ...settings.image, image_count: parseInt(e.target.value) } })}>
                                    {["4", "6", "8", "10"].map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>
                            <div className="settings-row">
                                <label className="settings-label">BROADCAST MODE:</label>
                                <select className="input-field" value={settings.pipeline.upload_mode} style={{ background: 'var(--accent-sec)', width: '150px' }} onChange={(e) => setSettings({ ...settings, pipeline: { ...settings.pipeline, upload_mode: e.target.value } })}>
                                    <option value="public">public</option>
                                    <option value="unlisted">unlisted</option>
                                    <option value="draft">draft</option>
                                </select>
                            </div>

                            {/* CHROME PROFILES SECTION */}
                            <div className="settings-section-title" style={{ marginTop: '40px' }}>⬡ CHROME PROFILES · <span style={{ color: 'var(--accent-pri)' }}>YOUTUBE UPLOAD</span></div>
                            <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid #111', borderRadius: '4px', padding: '20px', marginBottom: '20px' }}>
                                <div style={{ marginBottom: '20px' }}>
                                    <label className="settings-label" style={{ marginBottom: '10px', display: 'block' }}>ACTIVE PROFILE:</label>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                                        {settings.pipeline.chrome_profiles && settings.pipeline.chrome_profiles.length > 0 ? (
                                            settings.pipeline.chrome_profiles.map((p: any, idx: number) => (
                                                <div
                                                    key={idx}
                                                    onClick={() => setSettings({ ...settings, pipeline: { ...settings.pipeline, active_profile_index: idx } })}
                                                    className={`chip ${settings.pipeline.active_profile_index === idx ? 'active-cyan' : ''}`}
                                                    style={{ cursor: 'pointer' }}
                                                >
                                                    {p.name}
                                                </div>
                                            ))
                                        ) : (
                                            <div className="Mono" style={{ fontSize: '10px', color: 'var(--text-sec)', opacity: 0.5 }}>NO PROFILES CONFIGURED</div>
                                        )}
                                    </div>
                                    <div style={{ marginTop: '10px' }}>
                                        {settings.pipeline.chrome_profiles && settings.pipeline.chrome_profiles.length > 0 && (
                                            <button 
                                                onClick={() => removeProfile(settings.pipeline.active_profile_index)}
                                                className="btn-outline-red" 
                                                style={{ padding: '4px 10px', fontSize: '9px' }}
                                            >
                                                🗑 REMOVE SELECTED PROFILE
                                            </button>
                                        )}
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', marginTop: '30px', borderTop: '1px solid #111', paddingTop: '20px' }}>
                                    <input
                                        type="text"
                                        className="input-field"
                                        placeholder="New Profile Name (e.g. My Channel)"
                                        value={profileName}
                                        onChange={(e) => setProfileName(e.target.value)}
                                        style={{ flex: 1 }}
                                    />
                                    <button
                                        onClick={setupNewProfile}
                                        disabled={launchingProfile}
                                        className="btn-primary"
                                        style={{ padding: '10px 20px', fontSize: '11px' }}
                                    >
                                        {launchingProfile ? "LAUNCHING..." : "➕ SETUP NEW PROFILE"}
                                    </button>
                                    <button
                                        onClick={scanExistingProfiles}
                                        className="btn-primary"
                                        style={{ padding: '10px 20px', fontSize: '11px', background: 'var(--accent-sec)', border: '1px solid var(--accent-sec)' }}
                                    >
                                        🔍 SCAN D:\ PROFILES
                                    </button>
                                </div>
                                <p className="Mono" style={{ fontSize: '9px', color: 'var(--text-sec)', marginTop: '15px', opacity: 0.6 }}>
                                    * Setup will open a Chrome window on your desktop. Log in to YouTube manually once.
                                </p>
                            </div>

                            {/* SAVE BUTTON */}
                            <button onClick={saveSettings} className="btn-primary" style={{ width: '100%', marginTop: '60px', padding: '18px', fontSize: '14px' }}>💾 SAVE CONFIGURATION</button>
                        </div>
                    </div>
                )}

                {activeTab === "history" && (
                    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                        <div className="glass" style={{ border: '1px solid var(--border)', borderRadius: '12px', padding: '60px', textAlign: 'center' }}>
                            <div style={{ fontSize: '40px', marginBottom: '20px' }}>📜</div>
                            <h2 className="Orbitron" style={{ fontSize: '20px', color: 'var(--accent-pri)', marginBottom: '10px' }}>NEURAL ARCHIVE</h2>
                            <p className="Mono" style={{ color: 'var(--text-sec)', fontSize: '12px' }}>Your video job history is securely synced from the Supabase cloud.</p>
                            <p className="Mono" style={{ color: 'var(--text-sec)', fontSize: '10px', marginTop: '20px', opacity: 0.5 }}>INTEGRATION ACTIVE v2.5</p>
                        </div>
                    </div>
                )}
            </main>

            {/* FOOTER */}
            <footer className="glass" style={{ padding: '12px 40px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: 'none', borderLeft: 'none', borderRight: 'none' }}>
                <div className="Mono" style={{ color: '#444', fontSize: '10px' }}>⬡ NEURAL CORE: {user.email} | SECURE_TUNNEL: ENCRYPTED</div>
                <div className="Orbitron" style={{ color: 'var(--accent-pri)', fontSize: '10px', letterSpacing: '1px' }}>
                    AUDIO [{settings.tts.backend.toUpperCase()}] · VISION [{settings.image.backend.toUpperCase()}]
                </div>
            </footer>
        </div>
    );
}
