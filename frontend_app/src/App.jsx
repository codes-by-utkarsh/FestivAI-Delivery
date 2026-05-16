import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [authMode, setAuthMode] = useState('login')
  const [activeTab, setActiveTab] = useState('dashboard')
  
  // Live Data States
  const [companies, setCompanies] = useState([])
  const [festivals, setFestivals] = useState([])
  const [usersList, setUsersList] = useState([])
  const [logs, setLogs] = useState([])
  const [stats, setStats] = useState({ total_companies: 0, active_agents: 0, videos_generated: 0, whatsapp_sent: 0 })
  
  // UI Interaction States
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isDispatching, setIsDispatching] = useState(false)
  
  // Dispatch Selections
  const [dashboardSelectedCompany, setDashboardSelectedCompany] = useState('')
  const [dashboardSelectedFestival, setDashboardSelectedFestival] = useState('')
  const [companyTabSelectedFestival, setCompanyTabSelectedFestival] = useState({})

  useEffect(() => {
    if (token) {
      fetchAllData()
    }
  }, [token])

  const fetchAllData = async () => {
    try {
      const headers = { 'Authorization': `Bearer ${token}` }
      
      // Fetch Companies
      const resComp = await fetch(`${API_BASE}/customers`, { headers })
      if (resComp.ok) {
        const dataComp = await resComp.json()
        setCompanies(dataComp.customers || [])
        if (dataComp.customers?.length > 0 && !dashboardSelectedCompany) {
          setDashboardSelectedCompany(dataComp.customers[0].customer_id)
        }
      }

      // Fetch Stats
      const resStats = await fetch(`${API_BASE}/stats`, { headers })
      if (resStats.ok) {
        const dataStats = await resStats.json()
        setStats(dataStats)
      }

      // Fetch Festivals
      const resFest = await fetch(`${API_BASE}/festivals`, { headers })
      if (resFest.ok) {
        const dataFest = await resFest.json()
        setFestivals(dataFest.festivals || [])
        if (dataFest.festivals?.length > 0 && !dashboardSelectedFestival) {
          setDashboardSelectedFestival(dataFest.festivals[0].name)
        }
      }

      // Fetch Users
      const resUsers = await fetch(`${API_BASE}/users-list`, { headers })
      if (resUsers.ok) {
        const dataUsers = await resUsers.json()
        setUsersList(dataUsers.users || [])
      }

      // Fetch Logs
      const resLogs = await fetch(`${API_BASE}/logs`, { headers })
      if (resLogs.ok) {
        const dataLogs = await resLogs.json()
        setLogs(dataLogs.logs || [])
      }

    } catch (e) {
      console.error("Error fetching live data:", e)
    }
  }

  const login = async (e) => {
    e.preventDefault()
    setIsLoggingIn(true)
    const email = e.target.email.value
    const password = e.target.password.value
    
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('token', data.access_token)
        setToken(data.access_token)
      } else {
        const err = await res.json()
        alert(`❌ Login failed: ${err.detail || 'Invalid credentials'}`)
      }
    } catch (e) {
      alert("❌ Network error connecting to backend API.")
    }
    setIsLoggingIn(false)
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setIsLoggingIn(true)
    const name = e.target.name.value
    const email = e.target.email.value
    const password = e.target.password.value
    const role = e.target.role.value
    
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, role })
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('token', data.access_token)
        setToken(data.access_token)
        alert(`✅ Successfully registered as ${role}! Welcome to SimplyPromised.`)
      } else {
        const err = await res.json()
        alert(`❌ Registration failed: ${err.detail || 'Server error'}`)
      }
    } catch (e) {
      alert("❌ Network error connecting to backend API.")
    }
    setIsLoggingIn(false)
  }

  const logout = () => {
    localStorage.clear()
    setToken(null)
  }

  const handleCreateCompany = async (e) => {
    e.preventDefault()
    setIsSubmitting(true)
    
    const formData = new FormData(e.target)
    const photos = e.target.photos.files
    
    if (photos.length < 8 || photos.length > 10) {
      alert("Please select between 8 and 10 photos for the video engine.")
      setIsSubmitting(false)
      return
    }

    try {
      const res = await fetch(`${API_BASE}/customers`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })

      if (res.ok) {
        alert("✅ Company onboarded successfully!")
        setIsModalOpen(false)
        fetchAllData()
      } else {
        const err = await res.json()
        alert(`❌ Onboarding failed: ${err.detail || 'Server error'}`)
        setIsModalOpen(false)
      }
    } catch (error) {
      alert("❌ Network error connecting to backend API.")
      setIsModalOpen(false)
    }
    setIsSubmitting(false)
  }

  const handleSendDirectWhatsApp = async (customerId, festivalName) => {
    if (!customerId) {
      alert("Please select a valid company first.");
      return;
    }
    if (!festivalName) {
      alert("Please select a valid festival first.");
      return;
    }
    
    setIsDispatching(true)
    alert(`Generating video for ${festivalName} and dispatching to WhatsApp... This may take 30-60 seconds.`)
    
    try {
      const res = await fetch(`${API_BASE}/send-whatsapp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          customer_id: customerId,
          festival_name: festivalName,
          template_name: "hello_world"
        })
      })

      if (res.ok) {
        const data = await res.json()
        alert(`✅ Video successfully generated and delivered! Meta Media ID: ${data.media_id}`)
        fetchAllData()
      } else {
        const err = await res.json()
        alert(`❌ Failed to send WhatsApp: ${err.detail || 'API Error'}`)
      }
    } catch (error) {
      alert('❌ Network error while connecting to the video engine server.')
    }
    setIsDispatching(false)
  }

  if (!token) {
    return (
      <div className="flex h-screen w-full relative overflow-y-auto">
        <div className="absolute inset-0 gradient-bg z-0 min-h-screen"></div>
        <div className="relative z-10 flex w-full min-h-screen p-6 md:p-12 items-center justify-center">
          <div className="hidden md:flex w-1/2 flex-col justify-center pr-16 text-white max-w-xl">
            <div className="inline-flex items-center gap-3 mb-8 glass px-5 py-3 rounded-2xl w-max">
              <div className="w-10 h-10 bg-gradient-to-tr from-orange-500 to-pink-500 rounded-xl flex items-center justify-center text-white shadow-lg"><i className="fa-solid fa-wand-magic-sparkles"></i></div>
              <h1 className="text-3xl font-bold tracking-tight">SimplyPromised</h1>
            </div>
            <h2 className="text-5xl font-extrabold mb-6 leading-tight drop-shadow-lg">Scale Your Brand's<br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-yellow-300">Emotional Connection.</span></h2>
            <p className="text-white/80 text-sm leading-relaxed mb-6">A production-grade festival marketing platform powered by FastAPI, Google Sheets, MoviePy video automation, and Meta WhatsApp Cloud API.</p>
            <div className="flex gap-4 text-xs font-semibold text-white/90">
              <div className="glass px-4 py-2 rounded-xl flex items-center gap-2"><i className="fa-solid fa-shield-halved text-orange-400"></i> Admin Access</div>
              <div className="glass px-4 py-2 rounded-xl flex items-center gap-2"><i className="fa-solid fa-user text-pink-400"></i> Agent Portal</div>
            </div>
          </div>
          <div className="w-full md:w-1/2 flex items-center justify-center">
            <div className="glass-card w-full max-w-md p-10 rounded-3xl shadow-2xl relative overflow-hidden my-8">
              <div className="relative z-10">
                {authMode === 'login' ? (
                  <>
                    <h2 className="text-3xl font-extrabold mb-2 text-gray-900 tracking-tight">Welcome Back</h2>
                    <p className="text-gray-500 text-sm mb-8 font-medium">Please enter your credentials to continue</p>
                    <form onSubmit={login}>
                      <div className="space-y-5 mb-8">
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Email</label>
                          <input name="email" type="email" defaultValue="admin@example.com" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3.5 outline-none focus:ring-2 focus:ring-orange-500/50" required />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Password</label>
                          <input name="password" type="password" defaultValue="adminpassword123" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3.5 outline-none focus:ring-2 focus:ring-orange-500/50" required />
                        </div>
                      </div>
                      <button type="submit" disabled={isLoggingIn} className="w-full bg-gradient-to-r from-orange-500 to-pink-500 text-white font-bold py-4 rounded-xl shadow-lg hover:-translate-y-0.5 transition-all mb-6">
                        {isLoggingIn ? "Logging in..." : "Sign In to Dashboard"}
                      </button>
                      <div className="text-center">
                        <button type="button" onClick={() => setAuthMode('register')} className="text-xs font-bold text-slate-700 hover:text-orange-600 transition-colors">
                          Don't have an account? <span className="text-orange-500 underline">Register New User</span>
                        </button>
                      </div>
                    </form>
                  </>
                ) : (
                  <>
                    <h2 className="text-3xl font-extrabold mb-2 text-gray-900 tracking-tight">Create Account</h2>
                    <p className="text-gray-500 text-sm mb-8 font-medium">Register as an Agent</p>
                    <form onSubmit={handleRegister}>
                      <div className="space-y-4 mb-8">
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1.5">Full Name</label>
                          <input name="name" type="text" placeholder="e.g. Priya Sharma" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-orange-500/50" required />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1.5">Email</label>
                          <input name="email" type="email" placeholder="e.g. priya@simplypromised.com" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-orange-500/50" required />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1.5">Password</label>
                          <input name="password" type="password" placeholder="••••••••" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-orange-500/50" required />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-1.5">Role</label>
                          <select name="role" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-orange-500/50 font-medium" required>
                            <option value="Agent">Agent</option>
                          </select>
                        </div>
                      </div>
                      <button type="submit" disabled={isLoggingIn} className="w-full bg-gradient-to-r from-orange-500 to-pink-500 text-white font-bold py-4 rounded-xl shadow-lg hover:-translate-y-0.5 transition-all mb-6">
                        {isLoggingIn ? "Registering..." : "Complete Registration"}
                      </button>
                      <div className="text-center">
                        <button type="button" onClick={() => setAuthMode('login')} className="text-xs font-bold text-slate-700 hover:text-orange-600 transition-colors">
                          Already have an account? <span className="text-orange-500 underline">Sign In</span>
                        </button>
                      </div>
                    </form>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'border-all' },
    { id: 'companies', label: 'Companies', icon: 'building' },
    { id: 'calendar', label: 'Festival Calendar', icon: 'calendar' },
    { id: 'videos', label: 'Videos', icon: 'film' },
    { id: 'whatsapp', label: 'WhatsApp', icon: 'whatsapp', fab: true },
    { id: 'users', label: 'Users', icon: 'user-group' },
    { id: 'settings', label: 'Settings', icon: 'gear' }
  ]

  return (
    <div className="flex h-screen w-full bg-[#fafafa]">
      {/* SIDEBAR */}
      <div className="w-64 bg-[#28325a] text-white flex flex-col h-full shrink-0 shadow-lg z-20">
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center shadow-lg"><i className="fa-solid fa-wand-magic-sparkles text-sm"></i></div>
            <div><h1 className="font-bold text-lg leading-none">SimplyPromised</h1><span className="text-[10px] uppercase text-white/70 tracking-widest font-medium">Festival Marketing Hub</span></div>
          </div>
        </div>
        
        <div className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`w-full flex items-center gap-4 px-4 py-3 rounded-lg text-sm transition-colors ${activeTab === tab.id ? 'bg-[#3b436e] text-white font-semibold' : 'text-[#a2a8c5] hover:bg-[#313962]'}`}>
              <i className={`w-4 text-center text-lg ${tab.fab ? 'fa-brands' : 'fa-solid'} fa-${tab.icon}`}></i>
              <span className="capitalize">{tab.label}</span>
              {activeTab === tab.id && <div className="absolute right-3 w-1.5 h-1.5 bg-orange-500 rounded-full shadow-[0_0_8px_#f97316]"></div>}
            </button>
          ))}
        </div>
        
        <div className="p-4 border-t border-[#3b436e] bg-[#28325a] cursor-pointer" onClick={logout}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#3b436e] flex justify-center items-center font-bold text-white shadow-md">A</div>
            <div><p className="text-sm font-bold text-white">Active Session</p><p className="text-xs text-[#a2a8c5]">Log out <i className="fa-solid fa-arrow-right-from-bracket ml-1"></i></p></div>
          </div>
        </div>
      </div>

      {/* CONTENT */}
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <div className="h-16 bg-white border-b border-gray-100 flex items-center justify-end px-8 sticky top-0 z-30">
          <div className="flex items-center gap-2 text-gray-500 font-medium text-sm">
            <i className="fa-regular fa-calendar"></i>
            <span>Saturday, 16 May 2026</span>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-8 relative">
          
          {/* DASHBOARD TAB */}
          {activeTab === 'dashboard' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <div className="mb-8">
                <h2 className="text-3xl font-bold text-slate-900">Dashboard</h2>
                <p className="text-slate-500 text-sm mt-1">Welcome back! Here's your live festival marketing overview.</p>
              </div>

              {/* INSTANT DISPATCH PANEL */}
              <div className="bg-gradient-to-r from-orange-500 to-pink-500 p-6 rounded-2xl shadow-lg text-white mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center text-white font-bold"><i className="fa-solid fa-bolt"></i></div>
                  <div>
                    <h3 className="font-bold text-xl">Instant Video Dispatch</h3>
                    <p className="text-sm opacity-90">Select any company and festival to instantly generate and send a WhatsApp greeting video.</p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 items-end bg-white/10 p-4 rounded-xl backdrop-blur-sm border border-white/10">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider mb-2 opacity-90">Select Company</label>
                    <select 
                      value={dashboardSelectedCompany} 
                      onChange={(e) => setDashboardSelectedCompany(e.target.value)}
                      className="w-full bg-white text-slate-800 rounded-lg p-3 text-sm font-medium outline-none shadow-sm"
                    >
                      {companies.length === 0 && <option value="">No companies onboarded yet</option>}
                      {companies.map(c => (
                        <option key={c.customer_id} value={c.customer_id}>{c.company_name} ({c.owner_name})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider mb-2 opacity-90">Select Festival</label>
                    <select 
                      value={dashboardSelectedFestival} 
                      onChange={(e) => setDashboardSelectedFestival(e.target.value)}
                      className="w-full bg-white text-slate-800 rounded-lg p-3 text-sm font-medium outline-none shadow-sm"
                    >
                      {festivals.length === 0 && <option value="">No festivals available</option>}
                      {festivals.map(f => (
                        <option key={f.festival_id} value={f.name}>{f.name} ({f.date})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <button 
                      onClick={() => handleSendDirectWhatsApp(dashboardSelectedCompany, dashboardSelectedFestival)}
                      disabled={isDispatching || companies.length === 0 || festivals.length === 0}
                      className="w-full bg-white text-orange-600 hover:bg-slate-50 font-bold py-3 rounded-lg shadow transition-colors flex items-center justify-center gap-2 text-sm"
                    >
                      <i className="fa-brands fa-whatsapp text-lg"></i>
                      {isDispatching ? "Generating & Sending..." : "Generate & Send Video Now"}
                    </button>
                  </div>
                </div>
              </div>

              {/* LIVE STATS */}
              <div className="grid grid-cols-4 gap-6 mb-8">
                <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm text-slate-500 font-medium">Total Companies</p>
                    <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400"><i className="fa-solid fa-building"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold text-slate-900 mb-1">{stats.total_companies}</h3>
                  <p className="text-xs text-slate-400">Active subscriptions</p>
                </div>
                
                <div className="bg-[#f59e0b] p-6 rounded-2xl shadow-sm text-white flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm font-medium opacity-90">Active Agents</p>
                    <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center"><i className="fa-solid fa-user-group"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold mb-1">{stats.active_agents}</h3>
                  <p className="text-xs opacity-80">Currently registered</p>
                </div>
                
                <div className="bg-[#3730a3] p-6 rounded-2xl shadow-sm text-white flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm font-medium opacity-90">Videos Generated</p>
                    <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center"><i className="fa-solid fa-video"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold mb-1">{stats.videos_generated}</h3>
                  <p className="text-xs opacity-80">Total recorded logs</p>
                </div>
                
                <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm text-slate-500 font-medium">WhatsApp Sent</p>
                    <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400"><i className="fa-regular fa-comment"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold text-slate-900 mb-1">{stats.whatsapp_sent}</h3>
                  <p className="text-xs text-slate-400">Successfully delivered</p>
                </div>
              </div>

              {/* UPCOMING FESTIVALS */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="flex justify-between items-center mb-6 border-b border-gray-50 pb-4">
                  <h3 className="text-lg font-bold text-slate-800">Upcoming Festivals</h3>
                  <i className="fa-regular fa-calendar text-gray-400"></i>
                </div>
                
                <div className="space-y-4">
                  {festivals.length === 0 && <p className="text-slate-400 text-sm py-4 text-center">No festivals found in database.</p>}
                  {festivals.map((f) => (
                    <div key={f.festival_id} className="flex items-center justify-between p-4 bg-[#fcfcfc] rounded-xl border border-gray-50 hover:bg-white hover:shadow-sm transition-all">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-[#f05c42] flex items-center justify-center text-white shadow-sm"><i className="fa-regular fa-calendar"></i></div>
                        <div>
                          <p className="font-bold text-slate-800 text-sm">{f.name}</p>
                          <p className="text-xs text-slate-500">{f.date} • {f.type}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <select 
                          value={dashboardSelectedCompany} 
                          onChange={(e) => setDashboardSelectedCompany(e.target.value)}
                          className="bg-white border border-gray-200 text-slate-800 rounded-lg p-1.5 text-xs font-medium outline-none"
                        >
                          {companies.length === 0 && <option value="">No companies</option>}
                          {companies.map(c => (
                            <option key={c.customer_id} value={c.customer_id}>{c.company_name}</option>
                          ))}
                        </select>
                        <button 
                          onClick={() => handleSendDirectWhatsApp(dashboardSelectedCompany, f.name)}
                          disabled={isDispatching || companies.length === 0}
                          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow transition-colors"
                        >
                          <i className="fa-brands fa-whatsapp text-sm"></i> {isDispatching ? "Sending..." : "Dispatch Now"}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* COMPANIES TAB */}
          {activeTab === 'companies' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <div className="flex justify-between items-center mb-8">
                <div><h2 className="text-3xl font-bold text-slate-900">Companies</h2></div>
                <button onClick={() => setIsModalOpen(true)} className="bg-orange-500 text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center gap-2 hover:bg-orange-600 transition-colors shadow-sm"><i className="fa-solid fa-plus"></i> Add Company</button>
              </div>

              {companies.length === 0 && (
                <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center shadow-sm">
                  <div className="w-16 h-16 bg-orange-50 text-orange-500 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl"><i className="fa-solid fa-building"></i></div>
                  <h3 className="font-bold text-xl text-slate-800 mb-1">No Companies Onboarded</h3>
                  <p className="text-slate-500 text-sm mb-6">Get started by adding your first client company to the platform.</p>
                  <button onClick={() => setIsModalOpen(true)} className="bg-orange-500 text-white px-6 py-3 rounded-xl font-bold text-sm shadow hover:bg-orange-600 transition-colors">Add First Company</button>
                </div>
              )}

              <div className="grid grid-cols-3 gap-6">
                {companies.map((c) => {
                  const currentFest = companyTabSelectedFestival[c.customer_id] || festivals[0]?.name || ''
                  return (
                    <div key={c.customer_id} className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-start mb-4">
                          <div className="w-12 h-12 rounded-lg bg-blue-600 text-white flex justify-center items-center font-bold text-xl">{c.company_name?.charAt(0) || 'C'}</div>
                          <span className="bg-emerald-50 text-emerald-600 px-3 py-1 rounded-full text-[10px] font-bold">Active</span>
                        </div>
                        <h3 className="font-bold text-lg text-slate-800">{c.company_name}</h3>
                        <p className="text-xs text-slate-500 mb-4">{c.owner_name}</p>
                        <div className="text-xs text-slate-600 space-y-2 mb-6">
                          <div className="flex items-center gap-2"><i className="fa-solid fa-phone text-slate-400 w-3"></i> {c.whatsapp}</div>
                          <div className="flex items-center gap-2"><i className="fa-solid fa-location-dot text-slate-400 w-3"></i> {c.address}</div>
                        </div>
                      </div>
                      
                      <div className="border-t border-gray-50 pt-4 flex flex-col gap-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[10px] text-slate-400">Select Festival:</span>
                          <select 
                            value={currentFest}
                            onChange={(e) => setCompanyTabSelectedFestival({...companyTabSelectedFestival, [c.customer_id]: e.target.value})}
                            className="bg-slate-50 border border-gray-200 text-slate-800 rounded p-1 text-xs font-medium flex-1"
                          >
                            {festivals.map(f => <option key={f.festival_id} value={f.name}>{f.name}</option>)}
                          </select>
                        </div>
                        <div className="flex justify-between items-center pt-1">
                          <span className="text-[10px] text-slate-400">Ends: {c.subscription_end}</span>
                          <button 
                            onClick={() => handleSendDirectWhatsApp(c.customer_id, currentFest)}
                            disabled={isDispatching || !currentFest}
                            className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow transition-colors"
                          >
                            <i className="fa-brands fa-whatsapp"></i> {isDispatching ? "Sending..." : "Send Video"}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* WHATSAPP TAB */}
          {activeTab === 'whatsapp' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <h2 className="text-3xl font-bold text-slate-900 mb-1">WhatsApp Distribution Logs</h2>
              <p className="text-slate-500 text-sm mb-6">Real-time delivery records from Meta Cloud API</p>
              
              <div className="bg-[#f97316] rounded-xl p-6 text-white mb-8 shadow-sm">
                <div className="flex gap-3">
                  <i className="fa-regular fa-comment mt-1"></i>
                  <div>
                    <h3 className="font-bold text-lg mb-1">Automated Delivery Pipeline</h3>
                    <p className="text-sm opacity-90">Videos are dynamically generated via MoviePy and dispatched instantly using Meta's Cloud Media API. View the live delivery history below.</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-gray-100"><h3 className="font-bold text-slate-800">Delivery Log</h3></div>
                {logs.length === 0 ? (
                  <p className="text-slate-400 text-sm p-8 text-center">No WhatsApp dispatch logs recorded yet.</p>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {logs.map((l) => (
                      <div key={l.log_id} className="p-6 flex items-center justify-between hover:bg-slate-50">
                        <div className="flex items-center gap-4">
                          <i className="fa-regular fa-comment text-slate-400"></i>
                          <div>
                            <p className="font-bold text-slate-800 text-sm">{l.company_name}</p>
                            <p className="text-xs text-slate-400">{l.whatsapp} • {l.festival_name} • {new Date(l.sent_at).toLocaleString()}</p>
                          </div>
                        </div>
                        <div className={`flex items-center gap-2 font-bold text-sm ${l.sent_status === 'Sent' ? 'text-green-600' : 'text-red-600'}`}>
                          <i className={`fa-regular ${l.sent_status === 'Sent' ? 'fa-circle-check' : 'fa-circle-xmark'}`}></i> {l.sent_status}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* USERS TAB */}
          {activeTab === 'users' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <div className="flex justify-between items-center mb-8">
                <div>
                  <h2 className="text-3xl font-bold text-slate-900 mb-1">User Management</h2>
                  <p className="text-slate-500 text-sm">System Access Control List</p>
                </div>
                <button className="bg-orange-500 text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center gap-2 hover:bg-orange-600 transition-colors shadow-sm"><i className="fa-solid fa-plus"></i> Add User</button>
              </div>
              
              <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
                {usersList.length === 0 ? (
                  <p className="text-slate-400 text-sm p-8 text-center">Loading users...</p>
                ) : (
                  <div className="divide-y divide-gray-100">
                    {usersList.map((u, i) => (
                      <div key={i} className="p-5 flex justify-between items-center hover:bg-slate-50 transition-colors">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-full bg-[#28325a] text-white flex items-center justify-center font-bold text-sm shadow-sm">
                            {u.name?.charAt(0) || 'U'}
                          </div>
                          <div>
                            <p className="font-bold text-slate-800 text-sm">{u.name}</p>
                            <p className="text-slate-400 text-xs">{u.email}</p>
                          </div>
                        </div>
                        {u.role === 'Admin' ? 
                          <span className="bg-orange-500 text-white px-4 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5"><i className="fa-solid fa-shield-halved"></i> Admin</span>
                          :
                          <span className="bg-slate-100 text-slate-600 px-4 py-1.5 rounded-full text-xs font-bold flex items-center gap-1.5"><i className="fa-solid fa-user"></i> Agent</span>
                        }
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* CALENDAR TAB */}
          {activeTab === 'calendar' && (
            <div className="max-w-6xl mx-auto animate-fade-in h-full flex flex-col">
              <h2 className="text-3xl font-bold text-slate-900 mb-1">Festival Calendar</h2>
              <p className="text-slate-500 text-sm mb-6">Indian festivals & holidays — videos auto-generate 1 day before each event</p>
              
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm flex-1 p-6">
                <div className="flex justify-between items-center mb-6">
                  <button className="w-8 h-8 rounded flex items-center justify-center hover:bg-slate-100 text-slate-600"><i className="fa-solid fa-chevron-left text-xs"></i></button>
                  <h3 className="font-bold text-lg text-slate-800">May 2026</h3>
                  <button className="w-8 h-8 rounded flex items-center justify-center hover:bg-slate-100 text-slate-600"><i className="fa-solid fa-chevron-right text-xs"></i></button>
                </div>
                
                <div className="grid grid-cols-7 gap-px bg-gray-100 rounded-xl overflow-hidden border border-gray-100">
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map(d => (
                    <div key={d} className="bg-white p-3 text-center text-xs font-medium text-slate-400">{d}</div>
                  ))}
                  
                  {/* Empty days */}
                  {Array(4).fill(0).map((_, i) => <div key={'e'+i} className="bg-white h-24 p-2 opacity-40"></div>)}
                  
                  {/* Days */}
                  {Array(31).fill(0).map((_, i) => {
                    const d = i + 1;
                    const hasEvent = d === 1 || d === 27;
                    return (
                      <div key={d} className="bg-white h-24 p-2 relative group hover:bg-slate-50 transition-colors cursor-pointer">
                        <span className={`text-xs font-medium ${d===16 ? 'w-6 h-6 bg-orange-500 text-white rounded-full flex items-center justify-center' : 'text-slate-600'}`}>{d}</span>
                        {d === 1 && <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-slate-600 bg-slate-100 px-1 py-0.5 rounded truncate"><i className="fa-solid fa-star text-orange-400"></i> May Day</div>}
                        {d === 27 && <div className="mt-1 flex items-center gap-1 text-[10px] font-bold text-slate-600 bg-slate-100 px-1 py-0.5 rounded truncate"><i className="fa-solid fa-star text-orange-400"></i> Eid-ul-Adha</div>}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col">
            <div className="flex justify-between items-center p-6 border-b border-gray-100">
              <h3 className="font-bold text-xl text-slate-900">Add Company</h3>
              <button onClick={() => setIsModalOpen(false)} className="w-8 h-8 rounded flex items-center justify-center hover:bg-slate-100 text-slate-400"><i className="fa-solid fa-xmark"></i></button>
            </div>
            <form onSubmit={handleCreateCompany} className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Company Name</label><input name="company_name" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Owner Name</label><input name="owner_name" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">WhatsApp Number</label><input name="whatsapp" placeholder="e.g. 919876543210" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Subscription Until</label><input name="subscription_end" type="date" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Company Address</label><input name="address" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Company Logo</label><input name="logo" type="file" accept="image/*" className="w-full bg-slate-50 border border-gray-200 p-1.5 rounded-lg text-sm" required/></div>
                <div className="col-span-2"><label className="block text-xs font-bold text-slate-700 mb-1.5">Product/Company Photos (Select 8 to 10 photos)</label><input name="photos" type="file" accept="image/*" multiple className="w-full bg-slate-50 border border-gray-200 p-1.5 rounded-lg text-sm" required/></div>
              </div>
              <div className="pt-4 flex justify-end gap-3 border-t border-gray-100 mt-6">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-5 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg font-bold">Cancel</button>
                <button type="submit" disabled={isSubmitting} className="px-5 py-2 text-sm bg-orange-500 text-white rounded-lg font-bold shadow hover:bg-orange-600 transition-colors">{isSubmitting ? "Uploading assets..." : "Save Company"}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
