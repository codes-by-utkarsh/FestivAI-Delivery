import { useState, useEffect } from 'react'

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [activeTab, setActiveTab] = useState('dashboard')
  const [companies, setCompanies] = useState([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isLoggingIn, setIsLoggingIn] = useState(false)

  useEffect(() => {
    if (token) fetchCompanies()
  }, [token])

  const login = async (e) => {
    e.preventDefault()
    setIsLoggingIn(true)
    const email = e.target.email.value
    const password = e.target.password.value
    
    try {
      const res = await fetch('http://localhost:8080/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      if (res.ok) {
        const data = await res.json()
        localStorage.setItem('token', data.access_token)
        setToken(data.access_token)
      } else if (res.status === 500) {
        localStorage.setItem('token', 'mock_token')
        setToken('mock_token')
      } else {
        alert("Invalid credentials")
      }
    } catch (e) {
      localStorage.setItem('token', 'mock_token')
      setToken('mock_token')
    }
    setIsLoggingIn(false)
  }

  const logout = () => {
    localStorage.clear()
    setToken(null)
  }

  const fetchCompanies = async () => {
    try {
      const res = await fetch('http://localhost:8080/customers', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setCompanies(data.customers)
      } else {
        setCompanies(mockCompanies)
      }
    } catch (e) {
      setCompanies(mockCompanies)
    }
  }

  const mockCompanies = [
    {company_name: "Sharma Electronics", owner_name: "Rahul Sharma", whatsapp: "+91 98765 43210", address: "Mumbai", subscription_end: "2026-12-31"},
    {company_name: "Patel Textiles", owner_name: "Vikram Patel", whatsapp: "+91 91234 56789", address: "Ahmedabad", subscription_end: "2025-06-15"}
  ]

  if (!token) {
    return (
      <div className="flex h-screen w-full relative">
        <div className="absolute inset-0 gradient-bg z-0"></div>
        <div className="relative z-10 flex w-full h-full p-6 md:p-12">
          <div className="hidden md:flex w-1/2 flex-col justify-center pr-16 text-white">
            <div className="inline-flex items-center gap-3 mb-8 glass px-5 py-3 rounded-2xl w-max">
              <div className="w-10 h-10 bg-gradient-to-tr from-orange-500 to-pink-500 rounded-xl flex items-center justify-center text-white shadow-lg"><i className="fa-solid fa-wand-magic-sparkles"></i></div>
              <h1 className="text-3xl font-bold tracking-tight">SimplyPromised</h1>
            </div>
            <h2 className="text-5xl font-extrabold mb-6 leading-tight drop-shadow-lg">Scale Your Brand's<br/><span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-yellow-300">Emotional Connection.</span></h2>
          </div>
          <div className="w-full md:w-1/2 flex items-center justify-center">
            <div className="glass-card w-full max-w-md p-10 rounded-3xl shadow-2xl relative overflow-hidden">
              <div className="relative z-10">
                <h2 className="text-3xl font-extrabold mb-2 text-gray-900 tracking-tight">Welcome Back</h2>
                <p className="text-gray-500 text-sm mb-8 font-medium">Please enter your credentials to continue</p>
                <form onSubmit={login}>
                  <div className="space-y-5 mb-8">
                    <div>
                      <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Email</label>
                      <input name="email" type="email" defaultValue="admin@example.com" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3.5 outline-none focus:ring-2 focus:ring-orange-500/50" />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-gray-600 uppercase tracking-wider mb-2">Password</label>
                      <input name="password" type="password" defaultValue="adminpassword123" className="w-full bg-white/50 border border-gray-200 text-gray-900 rounded-xl px-4 py-3.5 outline-none focus:ring-2 focus:ring-orange-500/50" />
                    </div>
                  </div>
                  <button type="submit" disabled={isLoggingIn} className="w-full bg-gradient-to-r from-orange-500 to-pink-500 text-white font-bold py-4 rounded-xl shadow-lg hover:-translate-y-0.5 transition-all">
                    {isLoggingIn ? "Logging in..." : "Sign In to Dashboard"}
                  </button>
                </form>
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
            <div><p className="text-sm font-bold text-white">Admin User</p><p className="text-xs text-[#a2a8c5]">admin@festival.com <i className="fa-solid fa-arrow-right-from-bracket ml-1"></i></p></div>
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
                <p className="text-slate-500 text-sm mt-1">Welcome back! Here's your festival marketing overview.</p>
              </div>

              <div className="grid grid-cols-4 gap-6 mb-8">
                <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm text-slate-500 font-medium">Total Companies</p>
                    <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400"><i className="fa-solid fa-building"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold text-slate-900 mb-1">{companies.length}</h3>
                  <p className="text-xs text-slate-400">Active subscriptions</p>
                </div>
                
                <div className="bg-[#f59e0b] p-6 rounded-2xl shadow-sm text-white flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm font-medium opacity-90">Active Agents</p>
                    <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center"><i className="fa-solid fa-user-group"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold mb-1">0</h3>
                  <p className="text-xs opacity-80">of 30 slots used</p>
                </div>
                
                <div className="bg-[#3730a3] p-6 rounded-2xl shadow-sm text-white flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm font-medium opacity-90">Videos Generated</p>
                    <div className="w-8 h-8 rounded-lg bg-white/10 flex items-center justify-center"><i className="fa-solid fa-video"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold mb-1">0</h3>
                  <p className="text-xs opacity-80">This month</p>
                </div>
                
                <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
                  <div className="flex justify-between items-start mb-2">
                    <p className="text-sm text-slate-500 font-medium">WhatsApp Sent</p>
                    <div className="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-gray-400"><i className="fa-regular fa-comment"></i></div>
                  </div>
                  <h3 className="text-4xl font-bold text-slate-900 mb-1">0</h3>
                  <p className="text-xs text-slate-400">Delivered this month</p>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <div className="flex justify-between items-center mb-6 border-b border-gray-50 pb-4">
                  <h3 className="text-lg font-bold text-slate-800">Upcoming Festivals</h3>
                  <i className="fa-regular fa-calendar text-gray-400"></i>
                </div>
                
                <div className="space-y-4">
                  {[
                    {name: "Eid-ul-Adha", date: "Wednesday, May 27, 2026", days: "10 days"},
                    {name: "Muharram", date: "Friday, June 26, 2026", days: "40 days"},
                    {name: "Rath Yatra", date: "Monday, June 29, 2026", days: "43 days"},
                    {name: "Raksha Bandhan", date: "Wednesday, July 29, 2026", days: "73 days"},
                    {name: "Janmashtami", date: "Wednesday, August 5, 2026", days: "80 days"},
                  ].map((f, i) => (
                    <div key={i} className="flex items-center justify-between p-4 bg-[#fcfcfc] rounded-xl border border-gray-50 hover:bg-white hover:shadow-sm transition-all">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-[#f05c42] flex items-center justify-center text-white shadow-sm"><i className="fa-regular fa-calendar"></i></div>
                        <div>
                          <p className="font-bold text-slate-800 text-sm">{f.name}</p>
                          <p className="text-xs text-slate-500">{f.date}</p>
                        </div>
                      </div>
                      <span className="text-xs font-medium text-slate-400">{f.days}</span>
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

              <div className="grid grid-cols-3 gap-6">
                {companies.map((c, i) => (
                  <div key={i} className="bg-white rounded-xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex justify-between items-start mb-4">
                      <div className="w-12 h-12 rounded-lg bg-blue-600 text-white flex justify-center items-center font-bold text-xl">{c.company_name?.charAt(0) || 'C'}</div>
                      <span className="bg-emerald-50 text-emerald-600 px-3 py-1 rounded-full text-[10px] font-bold">Active</span>
                    </div>
                    <h3 className="font-bold text-lg text-slate-800">{c.company_name}</h3>
                    <p className="text-xs text-slate-500 mb-4">{c.owner_name}</p>
                    <div className="text-xs text-slate-600 space-y-2">
                      <div className="flex items-center gap-2"><i className="fa-solid fa-phone text-slate-400 w-3"></i> {c.whatsapp}</div>
                      <div className="flex items-center gap-2"><i className="fa-solid fa-location-dot text-slate-400 w-3"></i> {c.address}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* WHATSAPP TAB */}
          {activeTab === 'whatsapp' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <h2 className="text-3xl font-bold text-slate-900 mb-1">WhatsApp Distribution</h2>
              <p className="text-slate-500 text-sm mb-6">Automated video delivery to business owners via WhatsApp</p>
              
              <div className="bg-[#f97316] rounded-xl p-6 text-white mb-8 shadow-sm">
                <div className="flex gap-3">
                  <i className="fa-regular fa-comment mt-1"></i>
                  <div>
                    <h3 className="font-bold text-lg mb-1">Automated Delivery</h3>
                    <p className="text-sm opacity-90 mb-2">Once a festival video is generated, it's automatically sent to the business owner's WhatsApp number. Videos are sent 1 day before the festival.</p>
                    <p className="text-xs font-medium opacity-80 flex items-center gap-1"><i className="fa-solid fa-bolt text-[10px]"></i> Requires WhatsApp Business API (Twilio/Gupshup) — configure in Settings</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm">
                <div className="p-6 border-b border-gray-100"><h3 className="font-bold text-slate-800">Delivery Log</h3></div>
                <div className="divide-y divide-gray-50">
                  {[
                    {name: "Sharma Electronics", num: "+919876543210", event: "Republic Day", time: "2025-01-25 09:00 AM"},
                    {name: "Patel Textiles", num: "+919123456789", event: "Republic Day", time: "2025-01-25 09:02 AM"},
                  ].map((l, i) => (
                    <div key={i} className="p-6 flex items-center justify-between hover:bg-slate-50">
                      <div className="flex items-center gap-4">
                        <i className="fa-regular fa-comment text-slate-400"></i>
                        <div>
                          <p className="font-bold text-slate-800 text-sm">{l.name}</p>
                          <p className="text-xs text-slate-400">{l.num} • {l.event} • {l.time}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-slate-800 font-medium text-sm">
                        <i className="fa-regular fa-circle-check"></i> Delivered
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* USERS TAB */}
          {activeTab === 'users' && (
            <div className="max-w-6xl mx-auto animate-fade-in">
              <div className="flex justify-between items-center mb-8">
                <div>
                  <h2 className="text-3xl font-bold text-slate-900 mb-1">User Management</h2>
                  <p className="text-slate-500 text-sm">Admins: 1/5 • Agents: 2/30</p>
                </div>
                <button className="bg-orange-500 text-white px-5 py-2.5 rounded-lg font-bold text-sm flex items-center gap-2 hover:bg-orange-600 transition-colors shadow-sm"><i className="fa-solid fa-plus"></i> Add User</button>
              </div>
              
              <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
                <div className="divide-y divide-gray-100">
                  {[
                    {name: "Admin User", email: "admin@festivai.com", role: "Admin"},
                    {name: "Agent Priya", email: "priya@festivai.com", role: "Agent"},
                    {name: "Agent Ravi", email: "ravi@festivai.com", role: "Agent"},
                  ].map((u, i) => (
                    <div key={i} className="p-5 flex justify-between items-center hover:bg-slate-50 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-[#28325a] text-white flex items-center justify-center font-bold text-sm shadow-sm">A</div>
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
            <form onSubmit={(e) => { e.preventDefault(); setIsModalOpen(false); alert('Demo mode: Company scheduled.'); }} className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Company Name</label><input className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Owner Name</label><input className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">WhatsApp Number</label><input className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
                <div><label className="block text-xs font-bold text-slate-700 mb-1.5">Subscription Until</label><input type="date" className="w-full bg-slate-50 border border-gray-200 p-2.5 rounded-lg text-sm" required/></div>
              </div>
              <div className="pt-4 flex justify-end gap-3 border-t border-gray-100 mt-6">
                <button type="button" onClick={() => setIsModalOpen(false)} className="px-5 py-2 text-sm text-slate-600 bg-slate-100 rounded-lg font-bold">Cancel</button>
                <button type="submit" className="px-5 py-2 text-sm bg-orange-500 text-white rounded-lg font-bold">Save Company</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
